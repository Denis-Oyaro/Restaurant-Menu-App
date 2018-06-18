from flask import Flask, render_template, url_for, redirect, request, jsonify
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Restaurant, MenuItem

engine = create_engine('postgres:///happyrestaurant')
DBSession = sessionmaker(bind = engine)
session = DBSession()

app = Flask(__name__)

@app.route('/')
@app.route('/restaurants')
def showRestaurants():
    restaurants = session.query(Restaurant).all()
    return render_template("restaurants.html", restaurants = restaurants)
    
@app.route('/restaurant/new', methods = ['GET', 'POST'])
def newRestaurant():
    if request.method == "POST":
        if request.form['newRestaurant']:
            new_restaurant_name = request.form['newRestaurant']
            new_restaurant = Restaurant(name = new_restaurant_name)
            session.add(new_restaurant)
            session.commit()
        return redirect(url_for('showRestaurants'))
    else:
        return render_template("newRestaurant.html")

@app.route('/restaurant/<int:restaurant_id>/edit', methods = ['GET', 'POST'])
def editRestaurant(restaurant_id):
    edit_restaurant = session.query(Restaurant).filter_by(id = restaurant_id).one()
    if request.method == 'POST':
        if request.form['editRestaurant']:
            edit_restaurant_name = request.form['editRestaurant']
            edit_restaurant.name = edit_restaurant_name
            session.add(edit_restaurant)
            session.commit()
        return redirect(url_for('showRestaurants'))
    else:
        return render_template("editRestaurant.html", restaurant = edit_restaurant)
    
@app.route('/restaurant/<int:restaurant_id>/delete', methods = ['GET', 'POST'])
def deleteRestaurant(restaurant_id):
    delete_restaurant = session.query(Restaurant).filter_by(id = restaurant_id).one()
    if request.method == 'POST':
        session.delete(delete_restaurant)
        session.commit()
        return redirect(url_for('showRestaurants'))
    else:
        return render_template("deleteRestaurant.html", restaurant = delete_restaurant)
    
@app.route('/restaurant/<int:restaurant_id>')
@app.route('/restaurant/<int:restaurant_id>/menu')
def showMenu(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id = restaurant_id).one()
    items = session.query(MenuItem).filter_by(restaurant_id = restaurant_id).all()
    return render_template("menu.html", items = items, restaurant = restaurant)
    
@app.route('/restaurant/<int:restaurant_id>/menu/new', methods = ['GET', 'POST'])
def newMenuItem(restaurant_id):
    if request.method == 'POST':
        new_name = request.form['item_name']
        new_description = request.form['item_description']
        new_price = request.form['item_price']
        new_course = request.form.get('item_course', None)
        if new_name and new_description and new_price and new_course:
            new_item = MenuItem(name = new_name, description = new_description, price = new_price, course = new_course, restaurant_id = restaurant_id)
            session.add(new_item)
            session.commit()
        return redirect(url_for("showMenu", restaurant_id = restaurant_id))
    else:
        return render_template("newMenuItem.html", restaurant_id = restaurant_id)
    
@app.route('/restaurant/<int:restaurant_id>/menu/<int:menu_id>/edit', methods = ['POST', 'GET'])
def editMenuItem(restaurant_id, menu_id):
    edit_item = session.query(MenuItem).filter_by(id = menu_id, restaurant_id = restaurant_id).one()
    if request.method == 'GET':
        return render_template("editMenuItem.html", item = edit_item)
    else:
        edit_item.name = request.form['item_name'] if request.form['item_name'] else edit_item.name
        edit_item.description = request.form['item_description'] if request.form['item_description'] else edit_item.description
        edit_item.price = request.form['item_price'] if request.form['item_price'] else edit_item.price
        edit_item.course = request.form['item_course']
        session.add(edit_item)
        session.commit()
        return redirect(url_for("showMenu", restaurant_id = restaurant_id))
        
@app.route('/restaurant/<int:restaurant_id>/menu/<int:menu_id>/delete', methods = ['GET', 'POST'])
def deleteMenuItem(restaurant_id, menu_id):
    delete_item = session.query(MenuItem).filter_by(id = menu_id, restaurant_id = restaurant_id).one()
    if request.method == "GET":
        return render_template("deleteMenuItem.html", item = delete_item)
    else:
        session.delete(delete_item)
        session.commit()
        return redirect(url_for('showMenu', restaurant_id = restaurant_id))
        
########### API endpoints ##########
@app.route('/restaurants/JSON')
def showRestaurantsJSON():
    restaurants = session.query(Restaurant).all()
    return jsonify(Restaurants = [restaurant.serialize for restaurant in restaurants])
    
@app.route('/restaurants/<int:restaurant_id>/menu/JSON')
def showMenuJSON(restaurant_id):
    items = session.query(MenuItem).filter_by(restaurant_id = restaurant_id).all()
    return jsonify(MenuItems = [item.serialize for item in items])
    
@app.route('/restaurants/<int:restaurant_id>/menu/<int:menu_id>/JSON')
def showMenuItemJSON(restaurant_id, menu_id):
    item = session.query(MenuItem).filter_by(restaurant_id = restaurant_id, id = menu_id).one()
    return jsonify(MenuItem = item.serialize)


if __name__ == "__main__":
    app.debug = True
    app.run(host = '0.0.0.0', port = 8080)