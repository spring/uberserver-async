from distutils.core import setup

setup(
    name="asyncio-spring",
    version="0.2.1",
    description="spring lobby client based on asyncio",
    author="Fox Wilson, TurBoss",
    author_email="fwilson@fwilson.me, j.l.toledano.l@gmail.com",
    url="https://github.com/TurBoss/asyncspring",
    install_requires=["blinker", 'pyCrypto'],
    packages=["asyncspring", "asyncspring.plugins"]
)
