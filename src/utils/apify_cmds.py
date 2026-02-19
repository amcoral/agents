# from typing import Any
# from apify_client import ApifyClient
# from os import getenv
# import logging

# logging.basicConfig(level=logging.INFO)

# CLIENT = ApifyClient(getenv("APIFY_KEY"))


# def run_actor(actor_id: str, run_input: dict[str, Any]) -> list[dict[str, Any]] | None:
# 	"""
# 	Run an Apify actor synchronously and get the resulting dataset items.

# 	:param actor_id: ID of the Apify actor to run
# 	:param run_input: JSON object specific to the Apify actor to use for the run. Must contain the exact parameters needed to run the actor.
# 	:return: List of JSON items from the dataset
# 	:rtype: list[dict[str, Any]] - a list of JSON objects each representing an item from the dataset as specified in the relevant actor's documentation.
# 	"""
# 	try:
# 		logging.info(f"Running actor {actor_id}")
# 		run: dict[str, Any] | None = CLIENT.actor(actor_id).call(run_input=run_input, timeout_secs=60000)
# 		if not run:
# 			return None
# 		items = []
# 		logging.info(run)
# 		items = CLIENT.dataset(run["defaultDatasetId"]).list_items().items
# 		logging.info(f"Finished actor {actor_id} with {len(items)} items")
# 		return items
# 	except Exception as e:
# 		logging.info(f"Error running actor {actor_id}: {e}")
# 		return []
