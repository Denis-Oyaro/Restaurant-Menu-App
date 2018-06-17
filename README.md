# Restaurant_menu_app
A web application for accessing and manipulating restaurant menus.<br/>
Steps:
1. Run vagrant to setup virtual machine with necessary software:
    * vagrant up
    * vagrant ssh
2. Cd to /vagrant and create database using following commands:
    * Run 'psql' ( this starts the progresSql program tool for interacting with posgreSql database).
    * Run 'create database happyrestaurant' to create database
    * Run '\q' to exit the psql tool
    * Run 'python database_setup.py' to create the tables in the database
3. Start the menu_app server application to listen for requests on port 8080:
    * python menu_app.py
