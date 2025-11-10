from django.urls import path
from . import views


urlpatterns = [
    # URLs de Autenticación
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    # URLs de Calificaciones (Listado y CRUD)
    path('', views.calificacion_list, name='calificacion_list'),
    path('ingresar/', views.calificacion_create, name='calificacion_create'),
    path('<int:pk>/eliminar/', views.calificacion_delete, name='calificacion_delete'),

    # Vistas de carga
    path('carga-factores/', views.carga_factores, name='carga_factores'),
    path('carga-montos/', views.carga_montos, name='carga_montos'),

    # Si usas estos en la tabla:
    path('<int:pk>/editar/', views.calificacion_edit, name='calificacion_edit'),
    path('<int:pk>/factores/', views.calificacion_factores, name='calificacion_factores'),
]
