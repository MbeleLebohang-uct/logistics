from firebase_functions import https_fn
from firebase_functions.options import set_global_options
from firebase_admin import initialize_app

set_global_options(region="africa-south1", max_instances=10)


initialize_app()


@https_fn.on_request()
def order_status_update_producer(req: https_fn.Request) -> https_fn.Response:
    return https_fn.Response("Hello Order Status Update Producer!")
