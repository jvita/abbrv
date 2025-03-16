from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
@app.route('/write')
def write():
    return render_template('writer.html')

@app.route('/draft')
def draft():
    # execute_on_refresh()
    return render_template('drafter.html')

@app.route('/rules')
def rules():
    # execute_on_refresh()
    return render_template('rules.html')

@app.route('/help')
def help():
    # execute_on_refresh()
    return render_template('help.html')

if __name__ == '__main__':
    # get_data()
    app.run(debug=True)
