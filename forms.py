from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, FloatField, SelectField, SubmitField, PasswordField
from wtforms.validators import DataRequired, Length, NumberRange

class LoginForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired(message='Это поле обязательно для заполнения')])
    password = PasswordField('Пароль', validators=[DataRequired(message='Это поле обязательно для заполнения')])
    submit = SubmitField('Войти')

class DishForm(FlaskForm):
    name = StringField('Название блюда', validators=[DataRequired()])
    description = TextAreaField('Описание')
    category = SelectField('Категория', validators=[DataRequired()])
    cost_price = FloatField('Себестоимость', validators=[
        DataRequired(),
        NumberRange(min=0, message='Себестоимость не может быть отрицательной')
    ])
    selling_price = FloatField('Цена продажи', validators=[
        DataRequired(),
        NumberRange(min=0, message='Цена продажи не может быть отрицательной')
    ])
    submit = SubmitField('Сохранить')

class WeeklyMenuForm(FlaskForm):
    day_of_week = SelectField('День недели', choices=[
        ('0', 'Понедельник'),
        ('1', 'Вторник'),
        ('2', 'Среда'),
        ('3', 'Четверг'),
        ('4', 'Пятница'),
        ('5', 'Суббота'),
        ('6', 'Воскресенье')
    ], validators=[DataRequired()])
    dish = SelectField('Блюдо', validators=[DataRequired()])
