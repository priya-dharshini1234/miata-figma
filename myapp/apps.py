from django.apps import AppConfig

class MyappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'myapp'

    def ready(self):
        import cloudinary
        cloudinary.config(
            cloud_name='dxuqakxv9',
            api_key='719323789754514',
            api_secret='hrrFtxLmlMJ4qJv4BozkxM_1yx4',
            secure=True,
        )