class ConsoleInput:
    def get_input(self) -> str:
        user_input = ''
        while not user_input:
            user_input = input('>')
        return user_input
