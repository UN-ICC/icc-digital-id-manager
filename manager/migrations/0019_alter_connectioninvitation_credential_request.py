# Generated by Django 3.2.15 on 2023-05-12 07:20

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('manager', '0018_credentialoffer_credential_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='connectioninvitation',
            name='credential_request',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='connection_invitations', to='manager.credentialrequest'),
        ),
    ]
