from flask import Flask, request, jsonify
from flask_cors import CORS
import g4f
from g4f.client import Client
from g4f.Provider import RetryProvider
import logging
import asyncio
import os
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize g4f client
client = Client()

# Basic runtime checks for g4f API surface
G4F_OK = {
    'has_chat': hasattr(client, 'chat') and hasattr(getattr(client, 'chat'), 'completions'),
    'has_images': hasattr(client, 'images') and callable(getattr(getattr(client, 'images'), 'generate', None)),
    'provider_module': hasattr(g4f, 'Provider')
}


def _safe_extract_text(resp):
    try:
        if resp is None:
            return None
        if hasattr(resp, 'choices') and resp.choices:
            c = resp.choices[0]
            if hasattr(c, 'message') and hasattr(c.message, 'content'):
                return c.message.content
            if isinstance(c, dict) and 'text' in c:
                return c['text']
        if isinstance(resp, dict) and 'choices' in resp and resp['choices']:
            c = resp['choices'][0]
            if isinstance(c, dict):
                if 'message' in c and isinstance(c['message'], dict) and 'content' in c['message']:
                    return c['message']['content']
                if 'text' in c:
                    return c['text']
        if hasattr(resp, 'content'):
            return resp.content
        return str(resp)
    except Exception:
        return str(resp)

# Thread pool for async operations
executor = ThreadPoolExecutor(max_workers=10)

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'status': 'online',
        'service': 'g4f Discord Bot API',
        'endpoints': {
            '/chat': 'POST - Generate text responses',
            '/image': 'POST - Generate images',
            '/providers': 'GET - List available providers'
        }
    })

@app.route('/chat', methods=['POST'])
def chat():
    """
    Generate text response using g4f
    Expects JSON: {
        "message": "user message",
        "model": "gpt-4" (optional, default: gpt-4),
        "provider": "provider_name" (optional),
        "conversation_history": [] (optional)
    }
    """
    try:
        data = request.json
        message = data.get('message', '')
        model = data.get('model', 'gpt-4')
        provider_name = data.get('provider', None)
        conversation_history = data.get('conversation_history', [])
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Build messages array
        messages = conversation_history.copy()
        messages.append({"role": "user", "content": message})
        
        # Prepare kwargs
        kwargs = {
            'model': model,
            'messages': messages
        }
        
        # Add provider if specified
        if provider_name:
            try:
                provider = getattr(g4f.Provider, provider_name)
                kwargs['provider'] = provider
            except AttributeError:
                logger.warning(f"Provider {provider_name} not found, using default")
        
        # Generate response
        response = client.chat.completions.create(**kwargs)
        
        response_text = _safe_extract_text(response)
        
        return jsonify({
            'success': True,
            'response': response_text,
            'model': model
        })
        
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/image', methods=['POST'])
def generate_image():
    """
    Generate image using g4f
    Expects JSON: {
        "prompt": "image description",
        "provider": "provider_name" (optional)
    }
    """
    try:
        data = request.json
        prompt = data.get('prompt', '')
        provider_name = data.get('provider', None)
        
        if not prompt:
            return jsonify({'error': 'Prompt is required'}), 400
        
        # Prepare kwargs
        kwargs = {
            'model': 'flux',
            'prompt': prompt
        }
        
        # Add provider if specified
        if provider_name:
            try:
                provider = getattr(g4f.Provider, provider_name)
                kwargs['provider'] = provider
            except AttributeError:
                logger.warning(f"Provider {provider_name} not found, using default")
        
        # Generate image
        response = client.images.generate(**kwargs)
        
        # Get image URL or data (robust)
        image_url = None
        try:
            if hasattr(response, 'data') and response.data:
                first = response.data[0]
                if hasattr(first, 'url'):
                    image_url = first.url
                elif isinstance(first, str):
                    image_url = first
            elif isinstance(response, str):
                image_url = response
        except Exception:
            image_url = None
        
        if not image_url:
            return jsonify({
                'success': False,
                'error': 'Failed to generate image'
            }), 500
        
        return jsonify({
            'success': True,
            'image_url': image_url,
            'prompt': prompt
        })
        
    except Exception as e:
        logger.error(f"Image generation error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/providers', methods=['GET'])
def list_providers():
    """List available g4f providers"""
    try:
        providers = []
        for name in dir(g4f.Provider):
            if not name.startswith('_'):
                attr = getattr(g4f.Provider, name)
                if isinstance(attr, type):
                    providers.append(name)
        
        return jsonify({
            'success': True,
            'providers': providers
        })
    except Exception as e:
        logger.error(f"Provider list error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/g4f-check', methods=['GET'])
def g4f_check():
    """Quick runtime check of g4f client capabilities."""
    try:
        return jsonify({
            'success': True,
            'g4f_ok': G4F_OK,
            'providers_available': [n for n in dir(g4f.Provider) if not n.startswith('_')] if hasattr(g4f, 'Provider') else []
        })
    except Exception as e:
        logger.error(f"g4f-check error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
