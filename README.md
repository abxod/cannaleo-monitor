# Cannaleo Monitor
## Motivation
Cannaleo, Germany's biggest B2B medical cannabis API provider for pharmacies, exposes an open API endpoint delivering a JSON object containing general information about the medical cannabis strains a given pharmacy currently has in stock, and most notably, their pharmacy-specific price and availability.

Having recognized this in December 2025, I got the idea to write an automated script to fetch this information from every pharmacy Cannaleo supports. Up
until March 2026, I'd been improving the script to be robust against the API, i.e., not dereference a possibly null JSON attribute, as I did not know how the JSON attributes were modeled in the background.

Starting from March 2026, I've been running this automated script 4 times a day, every day, using a GitHub workflow via GitHub's own runners. This allowed me to sample the price and availability of every cannabis strain from every pharmacy. Given this, I could then compare the price for a given strain from the previous run and compare it to the current's. This was a window into how often a strain's price changed and by how much. Interestingly, the prices fluctuate by a few cents throughout the day, which leads me to believe that the prices (set by the medicinal manufacturuers) change dynamically based on the market.

The script ran consistently with a few outages, caused by either a null-dereference prematurely terminating the script, which was promptly fixed, or by an IP block, fixed by longer waits between API calls.

Recently, I moved away from GitHub's runners to a self-hosted one run on a Raspberry Pi 5.

### Workflows
The project contains the following workflows:
- The data collection workflow, which executes inventory/fetch_inventories_from_api.py, runs automatically every 6 hours: This is responsible for dynamically fetching the supported pharmacies and iterating over their inventories' API endpoint. The data is diffed against previous data (for price/availability, etc. changes) and then uploaded to Supabase (in JSON or as rows), among other things.
- Once the database gets to a certain size, e.g., 4 million rows in the raw rows table, a workflow runs to back up this data to Cloudflare's R2 storage, since I'm using the free tier on Supabase.
- To be fixed: A workflow that fetches the images defined in the API response for each strain and automatically stores them in the DB.

### Frontend
What I'm aiming for is a dashboard interface that shows, among other things, the historical price average for a given strain, or a given manufacturer's strains. The frontend is currently a "webshop-like" interface in order to visualize the strains' attributes. The current implementation for the historical price graph is buggy, as it fetches the data from the raw snapshots table in order to compute the average for each point in time. The fix is to simply use another, already-existing DB table, however, I'm yet to get around to it.

**NOTE: The project is for PERSONAL reasons only. This is not being used for commercial purposes.**
