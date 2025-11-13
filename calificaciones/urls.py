# calificaciones/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    # Listado + CRUD
    path('', views.calificacion_list, name='calificacion_list'),
    path('ingresar/', views.calificacion_create, name='calificacion_create'),
    path('<int:pk>/editar/', views.calificacion_edit, name='calificacion_edit'),
    path('<int:pk>/eliminar/', views.calificacion_delete, name='calificacion_delete'),
    path('<int:pk>/factores/', views.calificacion_factores, name='calificacion_factores'),

    # Cargas masivas
    path('carga-factores/', views.carga_factores, name='carga_factores'),
    path('carga-factores/confirmar/', views.confirmar_carga_factores, name='confirmar_carga_factores'),
    path('carga-montos/', views.carga_montos, name='carga_montos'),
    path('<int:pk>/editar/', views.calificacion_edit, name='calificacion_edit'),
    path('<int:pk>/factores/', views.calificacion_factores, name='calificacion_factores'),
    path('carga-factores/', views.carga_factores, name='carga_factores'),
    path('carga-factores/confirmar/', views.confirmar_carga_factores, name='confirmar_carga_factores'),
    # NUEVA URL: Log de errores de la base de datos
    path('carga-factores/resultados/', views.carga_resultados_factores, name='carga_resultados_factores'),
]
