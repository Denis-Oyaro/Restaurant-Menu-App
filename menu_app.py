from flask import Flask, render_template, url_for, redirect, request, jsonify, flash
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Restaurant, MenuItem, User
from flask import session as login_session
import random, string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

CLIENT_ID = json.loads(open('client_secrets.json','r').read())['web']['client_id']

engine = create_engine('postgres:///happyrestaurantwithusers')
DBSession = sessionmaker(bind = engine)
session = DBSession()

app = Flask(__name__)


@app.route('/fbconnect', methods = ['POST'])
def fbconnect():
    # protect against cross-site request forgery attacks
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter'))
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data  # retrieve short-term access token
    # exchange client token for long-lived server token
    app_id = json.loads(open('fb_client_secrets.json','r').read())['web']['app_id']
    app_secret = json.loads(open('fb_client_secrets.json','r').read())['web']['app_secret']
    url = 'https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id={}&client_secret={}&fb_exchange_token={}'.format(app_id, app_secret, access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    # Extract access token
    token = json.loads(result)['access_token']
    url = "https://graph.facebook.com/v2.8/me?fields=name,id,email&access_token=%s" % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)
    #populate login_session
    login_session['provider'] = 'facebook'
    login_session['username'] = data['name']
    login_session['email'] = data['email']
    login_session['facebook_id'] = data['id']
    # The token must be stored in the login_session in order to properly logout
    login_session['access_token'] = token
    
    # Get user picture
    url = 'https://graph.facebook.com/v2.8/me/picture?access_token=%s&redirect=0&height=200&width=200' % token 
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)
    login_session['picture'] = data['data']['url']
    
    # see if user exists. If doesn't, make a new one.
    user_id = getUserID(login_session['email'])
    if user_id is None:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id
    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output
    
    
@app.route('/gconnect', methods = ['POST'])
def gconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter'))
        response.headers['Content-Type'] = 'application/json'
        return response
    code = request.data
    try:
        # upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json',scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(json.dumps('Failed to upgrade the authorization code.'))
        response.headers['Content-Type'] = 'application/json'
        return response
    #check that the access token is valid
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token={}'.format(access_token))
    h = httplib2.Http()
    result = json.loads(h.request(url,'GET')[1])
    # if there was an error in the access token info, abort
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')))
        response.headers['Content-Type'] = 'application/json'
        return response
    # Verify that the access token is used for the intended user
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(json.dumps("Token's user ID doesn't match given user ID."))
        response.headers['Content-Type'] = 'application/json'
        return response
    # Verify that the access token is valid for this app
    if result['issued_to'] != CLIENT_ID:
        response = make_response(json.dumps("Token's client ID does not match app's."))
        response.headers['Content-Type'] = 'application/json'
        return response
    # check to see if user is already logged in
    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and  gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'))
        response.headers['Content-Type'] = 'application/json'
        return response
        
    # store the access token in the session for later use.
    login_session['credentials'] = credentials
    login_session['gplus_id'] = gplus_id
    
    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer  = requests.get(userinfo_url, params = params)
    data = json.loads(answer.text)
    
    login_session['provider'] = 'google'
    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    
    # see if user exists. If doesn't, make a new one.
    user_id = getUserID(login_session['email'])
    if user_id is None:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id
        
    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output    
    
def gdisconnect():
    #only disconnect a connected user
    credentials = login_session.get('credentials')
    # Execute HTTP GET request to revoke access token
    access_token = credentials.access_token
    url = 'https://accounts.google.com/o/oauth2/revoke?token={}'.format(access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]

def fbdisconnect():
    facebook_id = login_session['facebook_id']
    access_token = login_session['access_token']
    url = 'https://graph.facebook.com/%s/permissions?access_token=%s' % (facebook_id,access_token)
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    
# Disconnect - revoke a current user's token and reset their login session
@app.route('/disconnect')
def disconnect():
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
            del login_session['credentials']
            del login_session['gplus_id']
        if login_session['provider'] == 'facebook':
            fbdisconnect()
            del login_session['facebook_id']
            del login_session['access_token']
            
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['provider']
        flash("You have successfully been logged out.")
    else:
        flash("You were not logged in to begin with.")
    return redirect(url_for('showRestaurants'))
        
# create a state token to prevent request forgery.
# store it in the session for later validation.
@app.route('/login')
def showLogin():
    state = ''.join((random.choice(string.ascii_uppercase + string.digits) for i in range(32)))
    login_session['state'] = state
    return render_template('login.html', STATE = state)

@app.route('/')
@app.route('/restaurants')
def showRestaurants():
    restaurants = session.query(Restaurant).all()
    if 'username' not in login_session:
        return render_template("publicRestaurants.html", restaurants = restaurants)
    return render_template("restaurants.html", restaurants = restaurants)
    
@app.route('/restaurant/new', methods = ['GET', 'POST'])
def newRestaurant():
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == "POST":
        if request.form['newRestaurant']:
            new_restaurant_name = request.form['newRestaurant']
            new_restaurant = Restaurant(name = new_restaurant_name, user_id = login_session['user_id'])
            session.add(new_restaurant)
            session.commit()
        return redirect(url_for('showRestaurants'))
    else:
        return render_template("newRestaurant.html")

@app.route('/restaurant/<int:restaurant_id>/edit', methods = ['GET', 'POST'])
def editRestaurant(restaurant_id):
    if 'username' not in login_session:
        return redirect('/login')
    edit_restaurant = session.query(Restaurant).filter_by(id = restaurant_id).one()
    user_id = edit_restaurant.user_id
    if request.method == 'POST':
        if request.form['editRestaurant']:
            edit_restaurant_name = request.form['editRestaurant']
            edit_restaurant.name = edit_restaurant_name
            session.add(edit_restaurant)
            session.commit()
        return redirect(url_for('showMenu', restaurant_id = restaurant_id))
    else:
        if login_session['user_id'] == user_id:
            return render_template("editRestaurant.html", restaurant = edit_restaurant)
        output = ''
        output += '<html><script>'
        output += 'alert("You do not have authorization to this page.");'
        output += 'window.location.href = "{}";'.format(url_for('showMenu', restaurant_id = restaurant_id))
        output += '</script></html>'
        return output
    
@app.route('/restaurant/<int:restaurant_id>/delete', methods = ['GET', 'POST'])
def deleteRestaurant(restaurant_id):
    if 'username' not in login_session:
        return redirect('/login')
    delete_restaurant = session.query(Restaurant).filter_by(id = restaurant_id).one()
    user_id = delete_restaurant.user_id
    if request.method == 'POST':
        menu_items = session.query(MenuItem).filter_by(restaurant_id = restaurant_id)
        if list(menu_items):
            menu_items = menu_items.all()
            for item in menu_items:
                session.delete(item)
                session.commit()
        session.delete(delete_restaurant)
        session.commit()
        return redirect(url_for('showRestaurants'))
    else:
        if login_session['user_id'] == user_id:
            return render_template("deleteRestaurant.html", restaurant = delete_restaurant)
        output = ''
        output += '<html><script>'
        output += 'alert("You do not have authorization to this page.");'
        output += 'window.location.href = "{}";'.format(url_for('showMenu', restaurant_id = restaurant_id))
        output += '</script></html>'
        return output
    
@app.route('/restaurant/<int:restaurant_id>')
@app.route('/restaurant/<int:restaurant_id>/menu')
def showMenu(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id = restaurant_id).one()
    items = session.query(MenuItem).filter_by(restaurant_id = restaurant_id).all()
    creator = getUserInfo(restaurant.user_id)
    if creator.id == login_session.get('user_id'):
        return render_template("menu.html", items = items, restaurant = restaurant, creator = creator )
    return render_template("publicMenu.html", items = items, restaurant = restaurant, creator = creator )
    
@app.route('/restaurant/<int:restaurant_id>/menu/new', methods = ['GET', 'POST'])
def newMenuItem(restaurant_id):
    if 'username' not in login_session:
        return redirect('/login')
    restaurant = session.query(Restaurant).filter_by(id = restaurant_id).one()
    user_id = restaurant.user_id
    if request.method == 'POST':
        new_name = request.form['item_name']
        new_description = request.form['item_description']
        new_price = request.form['item_price']
        new_course = request.form.get('item_course', None)
        if new_name and new_description and new_price and new_course:
            new_item = MenuItem(name = new_name, description = new_description, price = new_price, course = new_course, restaurant_id = restaurant_id, user_id = login_session['user_id'])
            session.add(new_item)
            session.commit()
        return redirect(url_for("showMenu", restaurant_id = restaurant_id))
    else:
        if login_session['user_id'] == user_id:
            return render_template("newMenuItem.html", restaurant_id = restaurant_id)
        output = ''
        output += '<html><script>'
        output += 'alert("You do not have authorization to this page.");'
        output += 'window.location.href = "{}";'.format(url_for('showRestaurants'))
        output += '</script></html>'
        return output
    
@app.route('/restaurant/<int:restaurant_id>/menu/<int:menu_id>/edit', methods = ['POST', 'GET'])
def editMenuItem(restaurant_id, menu_id):
    if 'username' not in login_session:
        return redirect('/login')
    edit_item = session.query(MenuItem).filter_by(id = menu_id, restaurant_id = restaurant_id).one()
    user_id = edit_item.user_id
    if request.method == 'GET':
        if login_session['user_id'] == user_id:
            return render_template("editMenuItem.html", item = edit_item)
        output = ''
        output += '<html><script>'
        output += 'alert("You do not have authorization to this page.");'
        output += 'window.location.href = "{}";'.format(url_for('showRestaurants'))
        output += '</script></html>'
        return output
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
    if 'username' not in login_session:
        return redirect('/login')
    delete_item = session.query(MenuItem).filter_by(id = menu_id, restaurant_id = restaurant_id).one()
    user_id = delete_item.user_id
    if request.method == "GET":
        if login_session['user_id'] == user_id:
            return render_template("deleteMenuItem.html", item = delete_item)
        output = ''
        output += '<html><script>'
        output += 'alert("You do not have authorization to this page.");'
        output += 'window.location.href = "{}";'.format(url_for('showRestaurants'))
        output += '</script></html>'
        return output
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
    
def createUser(login_session):
    newUser = User(name = login_session['username'], email = login_session['email'], picture = login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email = login_session['email']).one()
    return user.id
    
def getUserInfo(user_id):
    user = session.query(User).filter_by(id = user_id).one()
    return user
    
def getUserID(email):
    try:
        user = session.query(User).filter_by(email = email).one()
        return user.id
    except:
        return None


if __name__ == "__main__":
    app.debug = True
    app.secret_key = 'pupsy_mupsy'
    app.run(host = '0.0.0.0', port = 8080)