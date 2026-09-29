with open("offeragent/me.txt",encoding="utf-8") as f:
    text=f.read()

print(text.count("\n") + 1)