from .admin_router import admin_router
from .user_routers.user_main import router as main_router
from .user_routers.user_profile import router as profile_router
from .user_routers.user_p2p import router as p2p_router
from .user_routers.user_deal import router as deal_router
from .user_routers.user_language import router as language_router


routers = [admin_router, main_router, profile_router, p2p_router, deal_router, language_router]