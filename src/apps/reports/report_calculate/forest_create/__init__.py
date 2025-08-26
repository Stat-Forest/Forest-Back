from apps.reports.report_calculate.forest_create.forest_large_volume import calculate_large_volume
from apps.reports.report_calculate.forest_create.forest_create_statement import calculate_forest_statement
from apps.reports.report_calculate.forest_create.seed_movement import calculate_seed_movement
from apps.reports.report_calculate.forest_create.pencil_preparation import calculate_make_pencil
from apps.reports.report_calculate.forest_create.sale_seedlings_suitable import calculate_sale_seedlings


calculators = {
    "Yopiq ildiz yirik hajmli": calculate_large_volume,
    "O'rmon barpo qilish bo'limi": calculate_forest_statement,
    "Urug' harakati": calculate_seed_movement,
    "Qalamcha tayyorlash": calculate_make_pencil,
    "Sotish uchun yaroqli ko‘chatlar": calculate_sale_seedlings
}