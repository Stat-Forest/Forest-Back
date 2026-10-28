"""
Ish kunlari hisobi (TZ §8, Q14/Q15/Q31/Q32).

Qoidalar: hodisa kuni hisobga kirmaydi, keyingi ish kuni 1-kun; shanba/yakshanba
va bayramlar ish kuni emas; ko'chirilgan ish kuni (dam olish kunida ishlash)
ish kuni hisoblanadi. Ko'rib chiqish 3 kuni — bir nechta segmentdan yig'iladi
(mahallaga qaytarilgan davr hisobdan chiqadi, qolgan kunlar davom etadi).
"""
from datetime import date, datetime, timezone as dt_timezone

from django.test import SimpleTestCase

from apps.yashil.services.workdays import (
    Calendar,
    add_workdays,
    count_workdays,
    delivery_deadline,
    is_workday,
    local_date,
    overdue_workdays,
    review_deadline,
    review_days_used,
)

EMPTY = Calendar()


class IsWorkdayTest(SimpleTestCase):
    def test_weekday_is_workday_and_weekend_is_not(self):
        self.assertTrue(is_workday(date(2027, 1, 11), EMPTY))   # dushanba
        self.assertFalse(is_workday(date(2027, 1, 9), EMPTY))   # shanba
        self.assertFalse(is_workday(date(2027, 1, 10), EMPTY))  # yakshanba

    def test_holiday_on_weekday_is_not_workday(self):
        cal = Calendar(holidays={date(2027, 1, 11)})
        self.assertFalse(is_workday(date(2027, 1, 11), cal))

    def test_moved_workday_on_weekend_is_workday(self):
        cal = Calendar(workdays={date(2027, 1, 9)})
        self.assertTrue(is_workday(date(2027, 1, 9), cal))


class AddWorkdaysTest(SimpleTestCase):
    def test_q31_three_days_from_monday_is_thursday(self):
        self.assertEqual(add_workdays(date(2027, 1, 11), 3, EMPTY), date(2027, 1, 14))

    def test_q32_ten_days_from_monday_skips_two_weekends(self):
        self.assertEqual(add_workdays(date(2027, 1, 11), 10, EMPTY), date(2027, 1, 25))

    def test_event_day_itself_is_not_counted(self):
        # juma kuni 1 ish kuni -> dushanba
        self.assertEqual(add_workdays(date(2027, 1, 8), 1, EMPTY), date(2027, 1, 11))

    def test_q15_holiday_and_moved_workday_change_the_deadline(self):
        cal = Calendar(holidays={date(2027, 1, 11)}, workdays={date(2027, 1, 9)})
        self.assertEqual(add_workdays(date(2027, 1, 8), 1, cal), date(2027, 1, 9))
        self.assertEqual(add_workdays(date(2027, 1, 8), 2, cal), date(2027, 1, 12))

    def test_zero_days_returns_start(self):
        self.assertEqual(add_workdays(date(2027, 1, 11), 0, EMPTY), date(2027, 1, 11))


class CountWorkdaysTest(SimpleTestCase):
    def test_counts_workdays_after_start_through_end_inclusive(self):
        self.assertEqual(count_workdays(date(2027, 1, 11), date(2027, 1, 14), EMPTY), 3)
        self.assertEqual(count_workdays(date(2027, 1, 8), date(2027, 1, 11), EMPTY), 1)

    def test_same_day_is_zero(self):
        self.assertEqual(count_workdays(date(2027, 1, 11), date(2027, 1, 11), EMPTY), 0)


class ReviewDeadlineTest(SimpleTestCase):
    """Segment = (boshlanish sanasi, tugash sanasi yoki None — hali ochiq)."""

    def test_single_open_segment(self):
        segs = [(date(2027, 1, 11), None)]
        self.assertEqual(review_deadline(segs, EMPTY), date(2027, 1, 14))
        self.assertEqual(review_days_used(segs, date(2027, 1, 12), EMPTY), 1)

    def test_q14_return_pauses_and_remaining_days_continue(self):
        # 11-yanvar yuborildi, 12-yanvar qaytarildi (1 kun sarflandi),
        # 15-yanvar qayta yuborildi -> qolgan 2 kun -> 19-yanvar
        segs = [(date(2027, 1, 11), date(2027, 1, 12)), (date(2027, 1, 15), None)]
        self.assertEqual(review_deadline(segs, EMPTY), date(2027, 1, 19))
        self.assertEqual(review_days_used(segs, date(2027, 1, 18), EMPTY), 2)

    def test_closed_segments_only_has_no_deadline(self):
        segs = [(date(2027, 1, 11), date(2027, 1, 12))]
        self.assertIsNone(review_deadline(segs, EMPTY))

    def test_used_days_never_exceed_elapsed(self):
        segs = [(date(2027, 1, 11), date(2027, 1, 20)), (date(2027, 1, 21), None)]
        self.assertEqual(review_days_used(segs, date(2027, 1, 22), EMPTY), 8)
        # muddat o'tib ketgan: qolgan 0 kun -> oxirgi muddat boshlanish kunining o'zi
        self.assertEqual(review_deadline(segs, EMPTY), date(2027, 1, 21))


class DeliveryAndOverdueTest(SimpleTestCase):
    def test_delivery_deadline_is_ten_workdays(self):
        self.assertEqual(delivery_deadline(date(2027, 1, 11), EMPTY), date(2027, 1, 25))

    def test_overdue_is_zero_on_or_before_deadline(self):
        self.assertEqual(overdue_workdays(date(2027, 1, 25), date(2027, 1, 25), EMPTY), 0)
        self.assertEqual(overdue_workdays(date(2027, 1, 25), date(2027, 1, 20), EMPTY), 0)

    def test_q23_overdue_counts_workdays_after_deadline(self):
        self.assertEqual(overdue_workdays(date(2027, 1, 25), date(2027, 1, 29), EMPTY), 4)
        self.assertEqual(overdue_workdays(date(2027, 1, 25), date(2027, 2, 1), EMPTY), 5)


class LocalDateTest(SimpleTestCase):
    def test_utc_evening_is_next_day_in_tashkent(self):
        # 2027-01-11 20:30 UTC = 2027-01-12 01:30 Asia/Tashkent
        self.assertEqual(local_date(datetime(2027, 1, 11, 20, 30, tzinfo=dt_timezone.utc)), date(2027, 1, 12))
