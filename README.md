# Order status updates middleware

## Firebase emulator

Setup the emulator using the instructions found [here](https://firebase.google.com/docs/emulator-suite/install_and_configure#install_the_local_emulator_suite)

Initialise the emulators using `firebase init emulators`

Start local development using `firebase emulators:start`


## Start the mock external api

On a new terminal, start the external api server using

```
$ cd external && flask run --host=0.0.0.0 --port=8000
```

## Start the mock erp api

On a new terminal, start the erp api server using

```
$ cd erp && flask run --host=0.0.0.0 --port=9000
```