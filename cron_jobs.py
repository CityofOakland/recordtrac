from public_records_portal.notifications import notify_due
from public_records_portal.db_helpers import create_viz_data
from public_records_portal.scribd_helpers import update_descriptions

# Notify city staff via e-mail if they belong to a request that is due soon or overdue:
notify_due()

# Create visualizations
create_viz_data()

# Update the Scribd document descriptions
# update_descriptions()
