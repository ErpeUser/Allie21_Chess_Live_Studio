"""Optional explicit cache warming of the official Allie weights (large download)."""
from allie_local_server import get_model
model = get_model()
print('Allie 2.1 model cached and ready:', type(model).__name__)
