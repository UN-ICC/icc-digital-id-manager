# Generated by Django 3.2.14 on 2022-07-15 08:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('manager', '0015_add_attributes_to_revocation'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='credentialoffer',
            name='cred_rev_id',
        ),
        migrations.RemoveField(
            model_name='credentialoffer',
            name='rev_reg_id',
        ),
        migrations.AddField(
            model_name='credentialoffer',
            name='cred_ex_id',
            field=models.CharField(max_length=250, null=True),
        ),
    ]
