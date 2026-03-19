from rest_framework.exceptions import Throttled
from rest_framework.throttling import UserRateThrottle


class AIDailyThrottle(UserRateThrottle):
    rate = "10/day"

    def wait(self):
        return super().wait()

    def throttle_failure(self):
        wait = self.wait()

        raise Throttled(
            detail="Kunlik AI limit tugadi.",
            wait=wait
        )