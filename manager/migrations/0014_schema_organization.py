# Generated by Django 3.1 on 2021-06-17 14:41
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def set_schema_organization(apps, schema_editor):
    Organization = apps.get_model('manager', 'Organization')
    Schema = apps.get_model('manager', 'Schema')

    organization_name = getattr(settings, "ORGANIZATION", "UNICC")
    organization, _ = Organization.objects.get_or_create(name=organization_name)
    Schema.objects.update(organization=organization)


class Migration(migrations.Migration):

    dependencies = [
        ('manager', '0013_auto_20210325_1049'),
    ]

    operations = [
        migrations.AddField(
            model_name='schema',
            name='organization',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='schemas', to='manager.organization'),
        ),
        migrations.RunPython(set_schema_organization, reverse_code=migrations.RunPython.noop)
    ]
