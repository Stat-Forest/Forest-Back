from celery import shared_task

from apps.billing.services import mib_push


@shared_task(name="billing.mib_push_contract", ignore_result=True)
def push_contract_to_mib(contract_id):
    mib_push.push_contract(contract_id)


@shared_task(name="billing.mib_push_retry_failed", ignore_result=True)
def retry_failed_mib_pushes():
    if mib_push.is_enabled():
        mib_push.retry_failed()


@shared_task(name="billing.mib_push_log_redact", ignore_result=True)
def redact_old_mib_push_logs():
    """Eski MIB loglaridagi ijarachi PII'sini maskalash (audit M1/F5)."""
    mib_push.redact_old_payloads()
