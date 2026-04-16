import requests
import json

def generate_chart_url(labels, data, chart_type='bar', title=''):
    """Generates a QuickChart.io URL for the given data."""
    config = {
        'type': chart_type,
        'data': {
            'labels': labels,
            'datasets': [{
                'label': title,
                'data': data,
                'backgroundColor': 'rgba(54, 162, 235, 0.5)',
                'borderColor': 'rgb(54, 162, 235)',
                'borderWidth': 1
            }]
        },
        'options': {
            'title': {
                'display': True,
                'text': title
            }
        }
    }
    
    encoded_config = json.dumps(config)
    return f"https://quickchart.io/chart?c={encoded_config}"
