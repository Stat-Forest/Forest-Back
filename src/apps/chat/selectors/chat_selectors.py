# from django.db.models import (
#     QuerySet,
#     Count,
#     Max,
#     Q,
# )
#
# from apps.chat.models.chat import Conversation
# from apps.users.models import CustomUser
#
#
# def get_support_dashboard_queryset() -> QuerySet[Conversation]:
#     """
#     Queue shown on support dashboard.
#
#     NEW conversations come first,
#     then TAKEN conversations.
#
#     Each conversation includes:
#
#         - user
#         - assigned_to
#         - unread_count
#         - last_message_at
#     """
#
#     return (
#         Conversation.objects
#         .select_related(
#             "user",
#             "assigned_to",
#         )
#         .annotate(
#             unread_count=Count(
#                 "messages",
#                 filter=Q(messages__is_read=False),
#             ),
#             messages_count=Count("messages"),
#             latest_message=Max("messages__created_at"),
#         )
#         .filter(
#             status__in=[
#                 Conversation.Status.NEW,
#                 Conversation.Status.TAKEN,
#             ]
#         )
#         .order_by(
#             "status",
#             "-last_message_at",
#         )
#     )
#
#
# def get_user_chat_list(
#     user: CustomUser,
# ) -> QuerySet[Conversation]:
#     """
#     Return conversations visible for user.
#     """
#
#     return (
#         Conversation.objects
#         .select_related(
#             "assigned_to",
#         )
#         .annotate(
#             unread_count=Count(
#                 "messages",
#                 filter=Q(
#                     messages__is_read=False,
#                 ),
#             )
#         )
#         .filter(
#             user=user,
#         )
#         .order_by(
#             "-last_message_at",
#         )
#     )
#
#
# def get_support_admin_chat_list(
#     support_admin: CustomUser,
# ) -> QuerySet[Conversation]:
#     """
#     Return conversations assigned to support admin.
#     """
#
#     return (
#         Conversation.objects
#         .select_related(
#             "user",
#         )
#         .annotate(
#             unread_count=Count(
#                 "messages",
#                 filter=Q(
#                     messages__is_read=False,
#                 ),
#             )
#         )
#         .filter(
#             assigned_to=support_admin,
#         )
#         .order_by(
#             "-last_message_at",
#         )
#     )
#
#
# def get_support_statistics():
#     """
#     Dashboard statistics.
#
#     Returns:
#
#         new
#         taken
#         closed
#     """
#
#     qs = Conversation.objects
#
#     return {
#         "new": qs.filter(
#             status=Conversation.Status.NEW,
#         ).count(),
#
#         "taken": qs.filter(
#             status=Conversation.Status.TAKEN,
#         ).count(),
#
#         "closed": qs.filter(
#             status=Conversation.Status.CLOSED,
#         ).count(),
#     }