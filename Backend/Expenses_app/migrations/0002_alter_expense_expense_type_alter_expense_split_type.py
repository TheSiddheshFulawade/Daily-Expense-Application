# Generated by Django 5.0.7 on 2024-07-31 13:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Expenses_app', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='expense',
            name='expense_type',
            field=models.CharField(choices=[('Personal', 'Personal'), ('Group', 'Group')], max_length=10),
        ),
        migrations.AlterField(
            model_name='expense',
            name='split_type',
            field=models.CharField(blank=True, choices=[('Equal', 'Equal'), ('Exact', 'Exact'), ('Percentage', 'Percentage')], max_length=10, null=True),
        ),
    ]
