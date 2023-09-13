# Social-image classification service

## Two inputs into an image pipeline

The Flask API exposes keyword and file-oriented paths. [crawler.py](crawler.py) handles retrieval, while [classifier/classify.py](classifier/classify.py) owns model-side classification. [app.py](app.py) connects those pieces through the API resources.

The useful review cases are an empty crawl, an unreadable image, and a model/resource failure. Keep retrieval results and model labels distinguishable in a demonstration, and measure accuracy on a representative labeled set before advertising classification quality.

#### System Dependencies
- Python 3.8+
#### Setup
- Navigate to the directory containing app.py
- Create a virtual environment using
```
python3 -m venv venv
```
- Activate the virtual environment using
```
source venv/bin/activate
```
- Install requirements using
```
pip install -r requirements.txt
```
- Run the server using
```
flask run
```
- The server will be live on `http://127.0.0.1:5000/`
​
#### API Working
##### Request
Endpoint: /keyword?keyword=car
Method: GET (Replace car with the keyword of your choice)
Response:
```
{
    "predictions": [{
        "filename": "abc",
        "label": "object",
        "probability": 50
    }]
}
```
​
​
Endpoint: /file
Method: POST (Send/Upload image using form-data with the keyname 'image')
Request:
```
{
    "image": file
}
````
​
Response:
```
{
    "predictions": [{
        "filename": "abc",
        "label": "object",
        "probability": 50
    }]
}
```
​
