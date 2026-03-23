import sys
import traceback

try:
    from api.routes.analytics import router
    print(f"ROUTES: {len(router.routes)}")
    for r in router.routes:
        if hasattr(r, "methods"):
            print(f"  {r.methods} {r.path}")
except Exception:
    traceback.print_exc()
