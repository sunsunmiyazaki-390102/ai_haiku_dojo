from django.urls import path
from . import views
app_name = "compose"

urlpatterns = [
    path("", views.home, name="home"),
    path("session/new/", views.session_new, name="session_new"),
    path("session/<int:session_id>/", views.session_detail, name="session_detail"),
    path("session/<int:session_id>/draft/new/", views.draft_new, name="draft_new"),
    path("draft/<int:draft_id>/", views.draft_detail, name="draft_detail"),

    # 追加：改稿ページ
    path("draft/<int:draft_id>/next/", views.draft_next, name="draft_next"),
    path("session/<int:session_id>/move/add/", views.move_add, name="move_add"),   
]
