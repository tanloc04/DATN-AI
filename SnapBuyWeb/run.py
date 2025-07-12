from market import app
from market.routes import recommend_bp

app.register_blueprint(recommend_bp)

if __name__ == '__main__':
    app.run(debug=True)

