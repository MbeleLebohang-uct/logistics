from firebase_functions import scheduler_fn
from firebase_functions.options import set_global_options
from firebase_admin import initialize_app

set_global_options(region="africa-south1", max_instances=1)


initialize_app()


@scheduler_fn.on_schedule(schedule="every 1 hours", max_instances=1)
def order_status_update_producer(event: scheduler_fn.ScheduledEvent) -> None:
    print(f"Producer triggered by cron: {event}")
