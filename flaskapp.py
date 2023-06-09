from flask import * 
from flask import Flask,flash, session, render_template, request, redirect
from flask_mysqldb import MySQL
from tensorflow import keras
from tensorflow.keras.utils import load_img
import numpy as np
from flask_mail import Mail, Message
import pickle
import os

app = Flask(__name__) 
app.secret_key = b'_5#A2L"F4T8z\n\xec]/'


app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'healthcaresquad9@gmail.com'
app.config['MAIL_PASSWORD'] = 'Aish&Ana2022'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True

mail = Mail(app)

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'fightos' 



model = keras.models.load_model('model.h5')
model1 = pickle.load(open('model.pkl', 'rb'))




mysql = MySQL(app)

@app.route('/')
def index():
    session['loginSts']=False
    if(session['loginSts']==False):
        return render_template('index.html')

@app.route('/register')
def register():
    return render_template('register.html')

  
@app.route('/registeruser', methods = ['POST'])
def registerUser():
    name = request.form['name']
    email = request.form['email']
    password = request.form['password']
    cursor = mysql.connection.cursor()
    cursor.execute(''' SELECT email from user ''')
    emailL= cursor.fetchall()
    #print(emailL)
    for t in emailL:
        #print(t[0])
        if(t[0]==email):
            return render_template('register.html', msg="email already registered. Please login")
    else:
        cursor.execute(''' INSERT INTO user VALUES(%s,%s,%s)''',(name,email,password))
        mysql.connection.commit()
        cursor.close()
        flash("Registration Sucessfull !")
        return redirect(url_for('login'))


@app.route('/login')
def login():
    return redirect(url_for('index', _anchor="appointment"))

  
@app.route('/loginuser',methods = ['POST'])  
def loginuser():
    #global loginSts
    email=request.form['email']
    password=request.form['password']

    cursor = mysql.connection.cursor()
    cursor.execute(''' SELECT email, password from user ''')
    epL= cursor.fetchall()
    #print(epL)
    for t in epL:
        # print(t[0])
        # print(t[1])
        if(t[0]==email and t[1]==password):
            cursor.close()
            session['email']=email
            session['loginSts']=True
            return redirect(url_for('portal'))
    else:
        flash("Invalid Credentials")
        return redirect(url_for('login'))


@app.route('/logout')
def logout():
    session['loginSts']=False
    return redirect(url_for('index'))

@app.route('/forgetpass')
def forgetpass():
    return render_template('forgetpass.html',msg_txt='')


@app.route("/forgetpassemail",  methods = ['POST'])
def forgetpassemail():
    email = request.form['email']
    cursor = mysql.connection.cursor()
    cursor.execute(''' SELECT * from user ''')
    emailL= cursor.fetchall()
    #print(emailL)
    for t in emailL:
        #print(t[1])
        if(t[1]==email):
            msg = Message('Hello Fighter !', sender =  'healthcaresquad9@gmail.com', recipients = [email])
            msg.body = "Hey "+t[0] +", your password is - "+ t[2]
            mail.send(msg)
            return render_template('forgetpass.html', msg_txt="email sent") 
    else:
        return render_template('forgetpass.html', msg_txt="enter registerd email id") 

@app.route('/portal')
def portal():
    if(session['loginSts']==True):
        return render_template('portal.html',prediction_text='')
    else:
        return redirect(url_for('index'))

@app.route('/uploadimg', methods = ['POST'])
def uploadimg():
    if(session['loginSts']==True):
        email=session['email']
        #session['loginSts']=True
        destination_path=""
        fileobj = request.files['file']
        file_extensions =  ["JPG","JPEG","PNG"]
        uploaded_file_extension = fileobj.filename.rsplit(".",1)[1]
            #validating file extension
        if(uploaded_file_extension.upper() in file_extensions):
            destination_path= f"data/test/{fileobj.filename}"
            fileobj.save(destination_path)
            try:
                cursor = mysql.connection.cursor()
                #inserting data into table image
                cursor.execute(''' SELECT email from image WHERE email = %s''',(email,))
                record=cursor.fetchone()
                if(record == None ):
                    cursor.execute(''' INSERT INTO image (email,image) VALUES(%s,%s)''',(email,fileobj))
                    mysql.connection.commit()
                else:
                    cursor.execute(''' UPDATE image SET image = %s WHERE email= %s''',(fileobj,email))
                    mysql.connection.commit()
                
                flash('Image successfully uploaded')

                output= predictClass(destination_path)
                per=percen(destination_path)

                if(output=="detected"):
                    if not(os.path.exists(f"data/test/infected/{fileobj.filename}")):
                        os.rename(destination_path,f"data/test/infected/{fileobj.filename}")
                else:
                    if not(os.path.exists(f"data/test/notinfected/{fileobj.filename}")):
                        os.rename(destination_path,f"data/test/notinfected/{fileobj.filename}")

                #print(output)
                #print("predicion done ************")
                
                cursor.close()
                return render_template('portal.html', prediction_text='PCOS - {} '.format(output),detected = 'detected : {}%'.format(round(per[0][0]*100,2)) , not_detected ='not detected : {}%'.format(round(per[0][1]*100,2)))
                #return redirect(url_for('portal'))
            except Exception as error:
                #using flash function of flask to flash errors.
                flash(f"{error}")
                return redirect(url_for('portal'))
        else:
            flash("Only images are accepted (png, jpg, jpeg, gif)")
            return redirect(url_for('portal')) 
    else:
        return redirect(url_for('index'))


def percen(destination_path):
    image = load_img(destination_path, target_size=(224, 224))
    img = image.resize((224, 224))
    img = np.array(image)
    img = img / 255.0
    img = img.reshape(1,224,224,3)
    prediction = model.predict(img)
    return prediction

def predictClass(destination_path):

    image = load_img(destination_path, target_size=(224, 224))
    img = image.resize((224, 224))
    img = np.array(image)
    img = img / 255.0
    img = img.reshape(1,224,224,3)
    prediction = model.predict(img)
    l={"detected":prediction[0][0],"not detected":prediction[0][1]}
    j=prediction.max()
    return get_key(j,l)


def get_key(val,l):
    for key, value in l.items():
         if val == value:
             return key
 
    return "Upload a valid ultra sound image"

 
############################################################################################




@app.route("/predict")
def practice():
    """ return the rendered template """
    return render_template("predictor.html")


def check_user_input(input):
    try:
        # Convert it into integer
        val = int(input)
        
    except ValueError:
        try:                                                #BLOCK CAN BE REMOVED
            # Convert it into float
            val = float(input)
            
        except ValueError:
            val=str(input)
    return val


@app.route('/predict',methods=['POST'])
def predict():
    '''
    For rendering results on HTML GUI
    '''
    l=[]
    
    for x in request.form.values() :
         z=x
         if isinstance(check_user_input(x),int)== True:                                      #REMOVE CHECK_USER_INPUT()
                x=z
         elif isinstance(check_user_input(x),str)== True:                                    #REMOVE CHECK_USER_INPUT()
               if x == 'yes':
                    x=1
               elif x=='no':
                    x=0
               elif x=='regular':
                    x=2
               elif x == 'irregular':
                    x=4
               else:
                   return render_template('predictor.html', prediction_text='Kindly enter valid input ')
         else:                                                                                            #BLOCK CAN BE REMOVED
               return render_template('predictor.html', prediction_text='Kindly enter valid input ')    
         l.append(int(x))    
    
      
    final_features = [np.array(l)]
    prediction = model1.predict(final_features)

    output = round(prediction[0], 2)
    if output == 1:
        output ='Yes'
        
    elif output == 0:
        output ='No'

    return render_template('predictor.html', prediction_text='Do I have PCOS ? {}'.format(output))

@app.route('/predict_api',methods=['POST'])
def predict_api():
    '''
    For direct API calls trought request
    '''
    data = request.get_json(force=True)
    prediction = model1.predict([np.array(list(data.values()))])

    output = prediction[0]
    return jsonify(output)


if __name__ == '__main__':
    app.run(debug = True) 