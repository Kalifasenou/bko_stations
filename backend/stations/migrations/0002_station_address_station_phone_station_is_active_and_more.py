from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('stations', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='station',
            name='address',
            field=models.CharField(blank=True, default='', max_length=255, verbose_name='Adresse'),
        ),
        migrations.AddField(
            model_name='station',
            name='phone',
            field=models.CharField(blank=True, default='', max_length=20, verbose_name='Téléphone'),
        ),
        migrations.AddField(
            model_name='station',
            name='is_active',
            field=models.BooleanField(default=True, verbose_name='Active'),
        ),
        migrations.AddField(
            model_name='signalement',
            name='comment',
            field=models.CharField(blank=True, default='', max_length=255, verbose_name='Commentaire'),
        ),
        migrations.AlterField(
            model_name='signalement',
            name='timestamp',
            field=models.DateTimeField(default=django.utils.timezone.now, verbose_name='Date du signalement'),
        ),
        migrations.AddIndex(
            model_name='station',
            index=models.Index(fields=['brand'], name='stations_st_brand_idx'),
        ),
        migrations.AddIndex(
            model_name='station',
            index=models.Index(fields=['is_active'], name='stations_st_is_active_idx'),
        ),
        migrations.AddIndex(
            model_name='station',
            index=models.Index(fields=['latitude', 'longitude'], name='stations_st_lat_lon_idx'),
        ),
        migrations.AddIndex(
            model_name='signalement',
            index=models.Index(fields=['station', 'timestamp'], name='stations_si_station_ts_idx'),
        ),
        migrations.AddIndex(
            model_name='signalement',
            index=models.Index(fields=['fuel_type', 'status'], name='stations_si_fuel_status_idx'),
        ),
        migrations.AddIndex(
            model_name='signalement',
            index=models.Index(fields=['timestamp'], name='stations_si_timestamp_idx'),
        ),
        migrations.AddIndex(
            model_name='signalement',
            index=models.Index(fields=['ip'], name='stations_si_ip_idx'),
        ),
    ]
