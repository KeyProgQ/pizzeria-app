from databaser import newPizza

name = input("Enter pizza name: ")
price = float(input("Enter pizza price"))

newPizza(name, price)
print("New pizza successful created!")