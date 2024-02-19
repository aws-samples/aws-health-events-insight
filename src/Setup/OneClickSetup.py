from utils import DataCollectionSetup
from utils import MemberSetup

#Print pretty Box
def print_boxed_text(text):
    lines = text.strip().split('\n')
    max_length = max(len(line) for line in lines)
    
    print('═' * (max_length + 2))
    for line in lines:
        print(f' {line.ljust(max_length)} ')
    print('═' * (max_length + 2))

def get_user_choice():
    #Get user choice to get deployment type
    options = {'1': 'DataCollection Setup', '2': 'Member Setup'}
    while True:
        print("Select Deployment option:")
        for key, value in options.items():
            print(f"{key}. {value}")
        choice = input("Enter the number of your choice: ")
        if choice in options:
            return options[choice]
        else:
            print("Invalid option. Please choose 1, 2")

def main():
    selected_option = get_user_choice()
    if selected_option == 'DataCollection Setup':
        print_boxed_text("You selected: DataCollection Setup")
        DataCollectionSetup.setup()

    elif selected_option == 'Member Setup':
        print_boxed_text("You selected: Member Setup")
        MemberSetup.setup()

if __name__ == "__main__":
    main()
