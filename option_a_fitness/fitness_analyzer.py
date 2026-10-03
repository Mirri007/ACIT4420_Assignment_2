"""Domain objects and session analysis for the Smart Fitness Session Analyzer."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean


MIN_USABLE_OBSERVATIONS = 3
UNUSUAL_HEART_RATE_DELTA = 30
UNUSUAL_SKIN_RESPONSE_DELTA = 0.5
UNUSUAL_TEMPERATURE_DELTA = 1.0


@dataclass(frozen=True)
class ParticipantProfile:
    participant_id: str
    baseline_heart_rate: int
    baseline_skin_response: float
    baseline_temperature: float

    @classmethod
    def from_dict(cls, raw_profile: dict):
        return cls(
            participant_id=raw_profile["participant_id"],
            baseline_heart_rate=int(raw_profile["baseline_heart_rate"]),
            baseline_skin_response=float(raw_profile["baseline_skin_response"]),
            baseline_temperature=float(raw_profile["baseline_temperature"]),
        )


@dataclass(frozen=True)
class FitnessObservation:
    timestamp: int
    heart_rate: float
    skin_response: float
    temperature: float
    activity_level: float
    signal_quality: float

    @classmethod
    def from_dict(cls, row: dict):
        return cls(
            timestamp=int(row["timestamp"]),
            heart_rate=float(row["heart_rate"]),
            skin_response=float(row["skin_response"]),
            temperature=float(row["temperature"]),
            activity_level=float(row["activity_level"]),
            signal_quality=float(row["signal_quality"]),
        )


class FitnessSessionAnalyzer:
    """Summarize one session and classify it relative to personal baselines."""

    def __init__(
        self,
        profile: dict,
        session_id: str,
        observations: list[dict],
        rejected_observations: int = 0,
    ):
        self.profile = ParticipantProfile.from_dict(profile)
        self.session_id = session_id
        self.raw_observations = list(observations)
        self.rejected_observations = rejected_observations
        self.valid_observations = [
            FitnessObservation.from_dict(row) for row in self.raw_observations
        ]
        self.session_summary = self._build_summary()

    def _build_summary(self):
        total = len(self.raw_observations) + self.rejected_observations
        rejected = self.rejected_observations
        summary = {
            "session_id": self.session_id,
            "participant_id": self.profile.participant_id,
            "classification": "insufficient_data",
            "data_status": "insufficient_data",
            "valid_observations": len(self.valid_observations),
            "rejected_observations": rejected,
            "total_observations": total,
            "average_heart_rate": None,
            "min_heart_rate": None,
            "max_heart_rate": None,
            "average_skin_response": None,
            "average_temperature": None,
            "average_activity": None,
            "min_activity": None,
            "max_activity": None,
            "average_signal_quality": None,
            "heart_rate_vs_baseline": None,
            "skin_response_vs_baseline": None,
            "temperature_vs_baseline": None,
            "classification_reason": (
                f"fewer than {MIN_USABLE_OBSERVATIONS} usable observations"
            ),
        }
        if len(self.valid_observations) < MIN_USABLE_OBSERVATIONS:
            return summary

        summary["data_status"] = "usable"
        observations = sorted(self.valid_observations, key=lambda item: item.timestamp)
        heart_rates = [item.heart_rate for item in observations]
        skin_responses = [item.skin_response for item in observations]
        temperatures = [item.temperature for item in observations]
        activity_levels = [item.activity_level for item in observations]
        signal_qualities = [item.signal_quality for item in observations]

        averages = {
            "average_heart_rate": mean(heart_rates),
            "average_skin_response": mean(skin_responses),
            "average_temperature": mean(temperatures),
            "average_activity": mean(activity_levels),
            "average_signal_quality": mean(signal_qualities),
        }
        summary.update({key: round(value, 2) for key, value in averages.items()})
        summary["min_heart_rate"] = min(heart_rates)
        summary["max_heart_rate"] = max(heart_rates)
        summary["min_activity"] = min(activity_levels)
        summary["max_activity"] = max(activity_levels)
        summary["heart_rate_vs_baseline"] = round(
            averages["average_heart_rate"] - self.profile.baseline_heart_rate, 2
        )
        summary["skin_response_vs_baseline"] = round(
            averages["average_skin_response"] - self.profile.baseline_skin_response, 2
        )
        summary["temperature_vs_baseline"] = round(
            averages["average_temperature"] - self.profile.baseline_temperature, 2
        )

        if rejected / total >= 0.25:
            classification = "poor_quality"
            reason = "at least 25% of session observations were rejected"
        elif averages["average_signal_quality"] < 0.6:
            classification = "poor_quality"
            reason = "average signal quality was below 0.6"
        else:
            first_heart_rate = observations[0].heart_rate
            last_heart_rate = observations[-1].heart_rate
            trend = last_heart_rate - first_heart_rate
            unusual_reasons = []
            heart_rate_delta = (
                averages["average_heart_rate"] - self.profile.baseline_heart_rate
            )
            skin_response_delta = (
                averages["average_skin_response"] - self.profile.baseline_skin_response
            )
            temperature_delta = (
                averages["average_temperature"] - self.profile.baseline_temperature
            )
            low_activity = averages["average_activity"] <= 0.2
            if (
                low_activity
                and heart_rate_delta >= UNUSUAL_HEART_RATE_DELTA
            ):
                unusual_reasons.append(
                    f"heart rate was {heart_rate_delta:+.2f} bpm above personal baseline "
                    "despite low activity"
                )
            if (
                low_activity
                and abs(skin_response_delta) >= UNUSUAL_SKIN_RESPONSE_DELTA
            ):
                unusual_reasons.append(
                    f"skin response was {skin_response_delta:+.2f} from personal baseline"
                )
            if (
                low_activity
                and abs(temperature_delta) >= UNUSUAL_TEMPERATURE_DELTA
            ):
                unusual_reasons.append(
                    f"temperature was {temperature_delta:+.2f} from personal baseline"
                )

            if unusual_reasons:
                classification = "unusual"
                reason = "; ".join(unusual_reasons)
            elif (
                trend <= -12
                and first_heart_rate >= self.profile.baseline_heart_rate + 10
                and last_heart_rate <= self.profile.baseline_heart_rate + 8
            ):
                classification = "recovery"
                reason = "heart rate declined toward the participant baseline near the end"
            elif (
                averages["average_activity"] >= 0.68
                and averages["average_heart_rate"] >= self.profile.baseline_heart_rate + 35
            ):
                classification = "high_activity"
                reason = "average activity and heart rate indicate sustained high exertion"
            elif (
                averages["average_activity"] >= 0.35
                or averages["average_heart_rate"] >= self.profile.baseline_heart_rate + 15
            ):
                classification = "moderate_activity"
                reason = "movement and heart rate show moderate effort above resting baseline"
            elif (
                averages["average_activity"] <= 0.2
                and averages["average_heart_rate"] <= self.profile.baseline_heart_rate + 10
            ):
                classification = "resting"
                reason = "activity and heart rate remained close to resting baseline"
            else:
                classification = "moderate_activity"
                reason = "measurements fit a mixed or transitional activity level"

        summary["classification"] = classification
        summary["classification_reason"] = reason
        return summary