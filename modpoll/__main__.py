from modpoll.Main import Main

if __name__ == "__main__":
    while(True):
        try:
            m = Main()
            m.run()
        except AssertionError as e:
            print(f"Assertion error",e)

