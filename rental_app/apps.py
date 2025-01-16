from django.apps import AppConfig

class RentalAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'rental_app'

    def ready(self):
        import rental_app.signals  # 导入信号