# name = "Nurs"

# age = 20

# print(name)

# print(age)
# print(5 + 7)


# name = input("What is your name? ")
# age = int(input("How old are you?"))

# print("Hello " + name)
# print("Через год тебе будет", age + 1)

# if age >= 18:
#     print("Ты взрослый")
# else :
#     print("Ты еще ребенок")

# if name == "Nurs":
#     print("Привет, создатель программы!")
# else :
#     print("Привет, " + name)

# print("Hello " + name)

#! 1task
# print("Hello, Python", 10)

#? 2task

# a = 7
# b = 3

# print("Сумма:", a + b)
# print("Разность:" , a - b)
# print("Произведение:", a * b)

#! 3task

# name = input("Как тебя зовут?")
# age = int(input("Сколько тебе лет?"))

# print("Привет, " + name)
# print("Тебе: ", age , "лет")

#! 4task

# sum1 = int(input("Введите сумму: "))
# sum2 = int(input("Введите сумму: "))
# total = sum1 + sum2
# average = total / 2
# print("Общая сумма:", total)
# print("Среднее значение:", average)


# num = int(input("Введите число: "))
# print("Ваше число:", num)

#? 5task

# name = input("What is your name?")
# print(f"Имя пользователя: {name}")

#? 6task

# birth_year = int(input("When were you born?"))
# print(f"Ваш возраст: {2026 - birth_year}")

#? 7task

# num = int(input("Введите число: "))
# number = int(input("Введите еще одно число: "))

# print("Сумма:", num + number)
# print("разность", num - number)
# print("произведение", num * number)
# print("частное", num / number)

#! 8task

# age = int(input("Введите ваш возраст: "))

# if age >= 18:
#     print("Доступ разрешён")
# else:
#     print("Доступ запрещён")

#! 9task

# number = int(input("Введите число: "))

# if number % 2 == 0:
#     print("Четное число")
# else:
#     print("Нечетное число")


#! 10task

# number = int(input("Введите число: "))

# if number > 0:
#     print("Положительное число")
# elif number < 0:
#  print("Отрицательное число")
# else:
#     print("Ноль")

#! 11task

# age = int(input("Введите ваш возраст: "))

# if age < 18:
#     print("Вы несовершеннолетний")
# else:
#     print("Вы совершеннолетний")


#! 12task

# number = int(input("Введите число: "))

# if number % 3 == 0 and number % 5 == 0:
#     print("FizzBuzz")
# else:
#     print("Не FizzBuzz")

#! challenge

# number = int(input("Введите число: "))

# if number % 3 == 0 and number % 5 == 0:
#     print("FizzBuzz")
# elif number % 3 == 0:
#     print("Fizz")
# elif number % 5 == 0:
#     print("Buzz")
# else:
#     print(number)

#! for цикл

# for i in range(1, 11):
#     print(i)

#! четные числа от 1 до 20

# for i in range(1, 21):
#     if i % 2 == 0:
#         print(i)

#? Спроси число n

# n = int(input("Введите число n: "))

# for index in range(1, n + 1):
#     print(index)

#? Посчитай сумму чисел от 1 до 100

total = 0

for index in range(1, 101):
    total += index

print("Сумма чисел от 1 до 100:", total)
