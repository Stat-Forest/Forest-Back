from apps.reports.report_calculate.forest_create.catch_seed import calculate_catch_seed
from apps.reports.report_calculate.forest_create.education_seed import calculate_education_seed
from apps.reports.report_calculate.forest_create.forest_large_volume import calculate_large_volume
from apps.reports.report_calculate.forest_create.forest_create_statement import calculate_forest_statement
from apps.reports.report_calculate.forest_create.golofit_statement import calculate_golofit_statement
from apps.reports.report_calculate.forest_create.green_environment import calculate_green_environment
from apps.reports.report_calculate.forest_create.heavy_neighborhood import calculate_heavy_neighborhood
from apps.reports.report_calculate.forest_create.save_healthy import calculate_save_healthy
from apps.reports.report_calculate.forest_create.seed_movement import calculate_seed_movement
from apps.reports.report_calculate.forest_create.pencil_preparation import calculate_make_pencil
from apps.reports.report_calculate.forest_create.sale_seedlings_suitable import calculate_sale_seedlings
from apps.reports.report_calculate.forest_create.seed_movement_plan import calculate_seed_movement_plan
from apps.reports.report_calculate.forest_create.seedlings_sprouts import calculate_seedlings
from apps.reports.report_calculate.forest_create.terassa_statement import calculate_terrassa_statement


calculators = {
    "Yopiq ildiz yirik hajmli": calculate_large_volume,
    "O'rmon barpo qilish bo'limi": calculate_forest_statement,
    "Urug' harakati": calculate_seed_movement,
    "Urug' xarakati Reja": calculate_seed_movement_plan,
    "Qalamcha tayyorlash": calculate_make_pencil,
    "Sotish uchun yaroqli ko‘chatlar": calculate_sale_seedlings,
    "Ko‘chat va Nihol": calculate_seedlings,
    "Tut Ko'chat va Tut Nihol": calculate_catch_seed,
    "Og'ir mahalla": calculate_heavy_neighborhood,
    "Sog'liqni saqlash": calculate_save_healthy,
    "Talim muassasalariga yetkazib berilgan ko'chatlar": calculate_education_seed,
    "Yashil makonga Ko'chat yetkazib berish": calculate_green_environment,
    "Terassa": calculate_terrassa_statement,
    "Golofit": calculate_golofit_statement
}