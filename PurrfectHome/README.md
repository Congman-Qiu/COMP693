
# Lincoln Fitness | COMP639 Group Project | Group 12

## Technology stack
  
- Python3
- MySql
- Flask
- Jinja templates
- Bootstrap

## Build and Run - Steps

1. Create Database connection
- Create a new connect.py file in your project root folder
- Add below code there
- Replace the values with your details
```
dbuser = "root"  # YOUR MySQL USERNAME
dbpass = "Poi098!@"  # "YOUR PASSWORD"
dbhost = "localhost"  # "YOUR HOST"
dbport = "3306" # "YOUR PORT"
dbname = "lincolnfitness" # "YOUR DATABASE NAME"
```

2. Run below command in your terminal to install required dependencies
```
pip install -r requirements.txt
```

3. Run below command in your terminal to build and run the application
```
flask --app webapp.py --debug run
```

4. Open the provided URL in your browser 

## Assumptions

