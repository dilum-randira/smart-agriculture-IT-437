"""Interactive first-admin setup; never puts passwords in arguments or source."""
import getpass
from .schemas import NewUser
from .store import Store,default_path


def main():
    username=input('First local administrator username: ').strip()
    password=getpass.getpass('Password (12–128 characters): ')
    confirm=getpass.getpass('Confirm password: ')
    if password!=confirm:raise SystemExit('Passwords do not match; no account created')
    user=NewUser(username=username,password=password,role='admin')
    store=Store(default_path())
    store.bootstrap(user.username,user.password.get_secret_value())
    print('Administrator created. No default credentials exist. Storage:',store.path)


if __name__=='__main__':main()
