import asyncio
import json
import logging
import sys
import time
from typing import Any, Dict
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Ensure path
import sys; import os; sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # Auto-fixed path
logger = logging.getLogger(__name__)

try:
    from whitemagic.core.ganas.base import GanaCall, BaseGana
    from whitemagic.core.ganas.eastern_quadrant import (
        HornGana, NeckGana, RootGana, RoomGana, HeartGana, TailGana, WinnowingBasketGana
    )
    from whitemagic.core.ganas.southern_quadrant import (
        GhostGana, WillowGana, StarGana, ExtendedNetGana, WingsGana, ChariotGana, AbundanceGana
    )
    from whitemagic.core.ganas.western_quadrant import (
        StraddlingLegsGana, MoundGana, StomachGana, HairyHeadGana, NetGana, TurtleBeakGana, ThreeStarsGana
    )
    # Note: Using new names for North (Dipper, etc.)
    from whitemagic.core.ganas.northern_quadrant import (
        DipperGana, OxGana, GirlGana, VoidGana, RoofGana, EncampmentGana, WallGana
    )
except ImportError as e:
    logger.debug("CRITICAL IMPORT ERROR: %s", e)
    sys.exit(1)

class SystemAuditor:
    def __init__(self):
        self.results = {}
        self.start_time = time.time()
        self.ganas = []
        self._init_ganas()
        
    def _init_ganas(self):
        self.ganas = [
            # East
            HornGana(), NeckGana(), RootGana(), RoomGana(), HeartGana(), TailGana(), WinnowingBasketGana(),
            # South
            GhostGana(), WillowGana(), StarGana(), ExtendedNetGana(), WingsGana(), ChariotGana(), AbundanceGana(),
            # West
            StraddlingLegsGana(), MoundGana(), StomachGana(), HairyHeadGana(), NetGana(), TurtleBeakGana(), ThreeStarsGana(),
            # North
            DipperGana(), OxGana(), GirlGana(), VoidGana(), RoofGana(), EncampmentGana(), WallGana()
        ]
        
    async def audit_gana(self, gana: BaseGana) -> Dict[str, Any]:
        """Audit a single Gana"""
        try:
            # Use a generic 'status_report' or specific task based on Gana
            task = "status_report"
            state = {"audit_mode": True}
            
            # Specific task overrides for meaningful output
            if isinstance(gana, RootGana): task = "check_system_health"
            if isinstance(gana, NetGana): task = "detect_patterns"
            if isinstance(gana, ExtendedNetGana): task = "search_all_patterns"
            if isinstance(gana, GhostGana): task = "get_metrics_summary"
            if isinstance(gana, ChariotGana): task = "manage_archaeology"
            
            call = GanaCall(task=task, state_vector=state)
            result = await gana.invoke(call)
            
            return {
                "status": "PASS",
                "mansion": gana.mansion.name,
                "garden": gana.garden,
                "output_keys": list(result.output.keys()),
                "execution_time_ms": result.execution_time_ms
            }
        except Exception as e:
            logging.error(f"Audit failed for {gana.mansion.name}: {e}")
            return {
                "status": "FAIL",
                "mansion": gana.mansion.name,
                "error": str(e)
            }

    async def run_full_audit(self):
        logger.debug(f"=== STAR SYSTEM AUDIT: 28 MANSIONS ===")
        logger.debug(f"Timestamp: {datetime.now().isoformat()}")
        
        success_count = 0
        
        for gana in self.ganas:
            logger.debug(f"Probing {gana.mansion.name} ({gana.garden})...", end="", flush=True)
            res = await self.audit_gana(gana)
            self.results[gana.mansion.name] = res
            
            if res["status"] == "PASS":
                logger.debug(f" [PASS] ({res['execution_time_ms']:.2f}ms)")
                success_count += 1
            else:
                logger.debug(f" [FAIL] - {res.get('error')}")
        
        duration = time.time() - self.start_time
        logger.debug(f"\n=== AUDIT COMPLETE ===")
        logger.debug(f"Total Ganas: {len(self.ganas)}")
        logger.debug("Successful: %s", success_count)
        logger.debug(f"Failed: {len(self.ganas) - success_count}")
        logger.debug("Total Duration: %ss", duration)
        
        with open("audit_results.json", "w") as f:
            json.dump(self.results, f, indent=2)

if __name__ == "__main__":
    auditor = SystemAuditor()
    asyncio.run(auditor.run_full_audit())
