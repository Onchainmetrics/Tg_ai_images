import logging
import os
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters
)
from enum import Enum
from typing import Optional, Dict
import requests
import json
from typing import Dict
import time
import asyncio

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)
# Load environment variables
logger.info(f"Current working directory: {os.getcwd()}")
logger.info(f"Script directory: {os.path.dirname(os.path.abspath(__file__))}")
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
logger.info(f"Looking for .env file at: {env_path}")
logger.info(f"Does .env file exist? {os.path.exists(env_path)}")

load_dotenv(env_path)
logger.info("Environment variables after initial load:")
logger.info(f"LEO_API_KEY: {'Yes' if os.getenv('LEO_API_KEY') else 'No'}")
logger.info(f"TELEGRAM_TOKEN: {'Yes' if os.getenv('TELEGRAM_TOKEN') else 'No'}")



# States for conversation handler
class States(Enum):
    INITIAL_PROMPT = 1
    CHOOSING_PROMPT = 2    # New state for prompt choice
    REFERENCE_CHOICE = 3   # New state for yes/no on reference
    AWAITING_REFERENCE = 4 # Only if they chose to upload
    GENERATING_IMAGE = 5
    ITERATING_IMAGE = 6



class ContentGenerationBot:
    def __init__(self):
        self.user_data: Dict = {}
        

        
        # Check Leonardo configuration - use exact key name from .env
        self.leo_api_key = os.getenv("LEO_API_KEY")  # This should match the .env file exactly
        
        if not self.leo_api_key:
            # Debug the actual environment variable name
            env_vars = [k for k in os.environ.keys() if 'LEO' in k.upper()]
            logger.error(f"Leonardo-related environment variables found: {env_vars}")
            raise ValueError("Leonardo API key is required but not found in environment variables")
            
        # Initialize Leonardo configuration
        self.leo_api_url = "https://cloud.leonardo.ai/api/rest/v1"
        self.leo_headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Bearer {self.leo_api_key}"
        }
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
        """Start the conversation and ask for initial prompt."""
        user = update.message.from_user
        logger.info(f"User {user.first_name} started the conversation")
        
        welcome_message = (
            "👋 Welcome to the AI Content Generation Bot!\n\n"
            "I'll help you create amazing meme videos for your community. "
            "Let's follow these steps:\n\n"
            "1️⃣ First, tell me about your memecoin character and what kind of content you want to create\n"
            "2️⃣ We'll work together to create the perfect prompt\n"
            "3️⃣ Generate and refine images\n"
            "4️⃣ Create a video\n"
            "5️⃣ Add voice-over\n\n"
            "Please describe your character and what you'd like to create!"
        )
        
        await update.message.reply_text(welcome_message)
        return States.INITIAL_PROMPT

    async def handle_initial_prompt(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
        """First handler that enhances prompt with Leonardo"""
        user_text = update.message.text
        user_id = update.effective_user.id
        
        # Store original prompt
        self.user_data[user_id] = {'original_prompt': user_text}
        
        # Enhance prompt using Leonardo
        try:
            enhanced_prompt_response = requests.post(
                f"{self.leo_api_url}/prompt/improve",
                headers=self.leo_headers,
                json={"prompt": user_text}
            )
            if enhanced_prompt_response.status_code != 200:
                error_msg = enhanced_prompt_response.json().get('error', 'Unknown error')
                logger.error(f"[DEBUG] Prompt enhancement failed: {enhanced_prompt_response.text}")
                
                if "too long" in error_msg.lower():
                    await update.message.reply_text(
                        "📝 Your prompt is too long! Please keep it under 200 characters.\n\n"
                        f"Current length: {len(user_text)} characters\n\n"
                        "Please try again with a shorter description."
                    )
                else:
                    await update.message.reply_text(
                        "Sorry, I had trouble enhancing your prompt. Would you like to try again?"
                    )
                return States.INITIAL_PROMPT
                
            enhanced_prompt = enhanced_prompt_response.json()['promptGeneration']['prompt']
            self.user_data[user_id]['enhanced_prompt'] = enhanced_prompt
            
            # Ask user if they want to use the enhanced prompt
            await update.message.reply_text(
                f"I've enhanced your prompt. Here's what I suggest:\n\n"
                f"Original: {user_text}\n"
                f"Enhanced: {enhanced_prompt}\n\n"
                f"Would you like to:\n"
                f"1️⃣ Use this enhanced prompt\n"
                f"2️⃣ Try another enhancement\n"
                f"3️⃣ Use your original prompt\n"
                f"Please respond with 1, 2, or 3"
            )
            return States.CHOOSING_PROMPT
            
        except Exception as e:
            logger.error(f"Error enhancing prompt: {e}")
            await update.message.reply_text(
                "Sorry, there was an error enhancing your prompt. Would you like to try again?"
            )
            return States.INITIAL_PROMPT

    async def handle_prompt_choice(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
        """Handle user's choice about which prompt to use"""
        user_choice = update.message.text
        user_id = update.effective_user.id
        
        if user_choice not in ["1", "2", "3"]:
            await update.message.reply_text(
                "Please respond with 1, 2, or 3:\n"
                "1️⃣ Use enhanced prompt\n"
                "2️⃣ Try another enhancement\n"
                "3️⃣ Use original prompt"
            )
            return States.CHOOSING_PROMPT
            
        if user_choice == "2":
            
            original_prompt = self.user_data[user_id]['original_prompt']
            # Reuse handle_initial_prompt but with the original text
            context.user_data['original_text'] = original_prompt  # Store temporarily
            update.message.text = original_prompt  # Set the text to original prompt
            return await self.handle_initial_prompt(update, context)
            
        # Store the chosen prompt
        chosen_prompt = self.user_data[user_id]['enhanced_prompt'] if user_choice == "1" else self.user_data[user_id]['original_prompt']
        self.user_data[user_id]['final_prompt'] = chosen_prompt
        
        # Ask about reference image
        await update.message.reply_text(
            "Do you have a reference image you'd like to use?\n"
            "1️⃣ Yes, I'll upload an image\n"
            "2️⃣ No, generate from scratch\n"
            "Please respond with 1 or 2"
        )
        return States.REFERENCE_CHOICE

    async def handle_reference_choice(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
        """Handle whether user wants to use a reference image"""
        user_choice = update.message.text
        user_id = update.effective_user.id
        
        if user_choice not in ["1", "2"]:
            await update.message.reply_text(
                "Please respond with 1 or 2:\n"
                "1️⃣ Yes, I'll upload an image\n"
                "2️⃣ No, generate from scratch"
            )
            return States.REFERENCE_CHOICE
        
        if user_choice == "1":
            await update.message.reply_text("Please upload your reference image.")
            return States.AWAITING_REFERENCE
        else:
            # Proceed directly to generation without reference
            return await self.start_image_generation(update, context)

    async def handle_reference_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
        """Handle the uploaded reference image"""
        user_id = update.effective_user.id
        
        if user_id not in self.user_data or 'final_prompt' not in self.user_data[user_id]:
            await update.message.reply_text(
                "Sorry, I've lost track of your prompt. Let's start over.\n"
                "Please provide a new prompt for your image."
            )
            return States.INITIAL_PROMPT
        
        # Get the image file
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        
        # Store image info in user_data
        self.user_data[user_id]['reference_image'] = {
            'file_id': photo.file_id,
            'file_path': file.file_path
        }
        
        return await self.start_image_generation(update, context)

    async def handle_image_generation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
        """Handle the actual image generation process"""
        user_id = update.effective_user.id
        user_data = self.user_data.get(user_id, {})
        
        logger.info(f"[DEBUG] Starting image generation for user {user_id}")
        logger.info(f"[DEBUG] User data available: {user_data}")
        
        try:
            if 'reference_image' in user_data:
                logger.info(f"[DEBUG] Using reference image: {user_data['reference_image']['file_path']}")
                logger.info(f"[DEBUG] With refined prompt: {user_data['final_prompt']}")
                result = await self.generate_image_with_reference(
                    prompt=user_data['final_prompt'],
                    image_url=user_data['reference_image']['file_path']
                )
            else:
                logger.info("[DEBUG] No reference image, generating from scratch")
                result = await self.generate_image(user_data['final_prompt'])
            
            if result['status'] == 'success':
                self.user_data[user_id]['generated_images'] = [result['image_url']]
                
                # Send the generated image in sequence
                await update.message.reply_photo(
                    photo=result['image_url'],
                    caption="Generated Image"
                )
                
                # Ask for user preference
                await update.message.reply_text(
                    "What would you like to do?\n\n"
                    "1️⃣ Use this image\n"
                    "2️⃣ Generate new variations\n"
                    "3️⃣ Modify the prompt\n\n"
                    "Please respond with a number 1-3"
                )
                
                return States.ITERATING_IMAGE
            
            else:
                raise Exception(f"Generation failed: {result['error']}")
                
        except Exception as e:
            logger.error(f"Error in image generation: {e}")
            await update.message.reply_text(
                "Sorry, there was an error generating the images. Would you like to:\n\n"
                "1️⃣ Try again\n"
                "2️⃣ Modify the prompt\n\n"
                "Please respond with 1 or 2"
            )
            return States.GENERATING_IMAGE

    async def handle_image_iteration(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
        """Handle user's choice after seeing generated image"""
        user_choice = update.message.text
        user_id = update.effective_user.id
        
        if user_choice not in ["1", "2"]:
            await update.message.reply_text(
                "Please respond with 1 or 2:\n"
                "1️⃣ Try again\n"
                "2️⃣ Modify the prompt"
            )
            return States.ITERATING_IMAGE
        
        if user_choice == "1":
            # Try again with same prompt
            return await self.start_image_generation(update, context)
        else:
            # Clear the enhanced/final prompt but keep original for reference
            original_prompt = self.user_data[user_id].get('original_prompt', '')
            self.user_data[user_id] = {'original_prompt': original_prompt}
            await update.message.reply_text(
                "Please provide a new prompt for your image."
            )
            return States.INITIAL_PROMPT

    async def start_image_generation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
        """Handle the image generation process"""
        user_id = update.effective_user.id
        user_data = self.user_data.get(user_id, {})
        
        logger.info(f"[DEBUG] Entered start_image_generation")
        logger.info(f"[DEBUG] Starting image generation for user {user_id}")
        logger.info(f"[DEBUG] User data available: {user_data}")
        
        try:
            if 'reference_image' in user_data:
                logger.info("[DEBUG] Using reference image")
                result = await self.generate_image_with_reference(
                    prompt=user_data['final_prompt'],
                    image_url=user_data['reference_image']['file_path'],
                    message_obj=update.message
                )
            else:
                logger.info("[DEBUG] No reference image, generating from scratch")
                result = await self.generate_image(
                    prompt=user_data['final_prompt'],
                    message_obj=update.message
                )
            
            if result['status'] == 'success':
                # Send the generated image
                await update.message.reply_photo(
                    result['image_url'],
                    caption="Here's your generated image! Would you like to:\n"
                            "1️⃣ Try again\n"
                            "2️⃣ Modify the prompt\n"
                            "Please respond with 1 or 2"
                )
                return States.ITERATING_IMAGE
            else:
                await update.message.reply_text(
                    "Sorry, there was an error generating the images. Would you like to:\n"
                    "1️⃣ Try again\n"
                    "2️⃣ Modify the prompt\n"
                    "Please respond with 1 or 2"
                )
                return States.ITERATING_IMAGE
                
        except Exception as e:
            logger.error(f"Error in image generation: {str(e)}")
            await update.message.reply_text(
                "Sorry, there was an error generating the images. Would you like to:\n"
                "1️⃣ Try again\n"
                "2️⃣ Modify the prompt\n"
                "Please respond with 1 or 2"
            )
            return States.ITERATING_IMAGE

    async def generate_image(self, prompt: str, message_obj) -> Dict:
        """Generate image using Leonardo.ai without reference"""
        try:
            processing_message = await message_obj.reply_text(
                "🎨 Generating your image...\n"
                "This might take a minute or two. Please wait..."
            )
            
            generation_url = f"{self.leo_api_url}/generations"
            payload = {
                "height": 512,
                "width": 1040,
                "modelId": "6b645e3a-d64f-4341-a6d8-7a3690fbf042",
                "prompt": prompt,
                "photoReal": False,
                "guidance_scale": 8,
                "num_images": 1
            }
            
            logger.info(f"[DEBUG] Sending generation request with payload: {payload}")
            response = requests.post(
                generation_url,
                headers=self.leo_headers,
                json=payload
            )
            
            if response.status_code != 200:
                logger.error(f"[DEBUG] Generation failed: {response.text}")
                return {'status': 'error', 'error': f"Generation failed with status {response.status_code}"}
            
            generation_id = response.json()['sdGenerationJob']['generationId']
            logger.info(f"[DEBUG] Got generation ID: {generation_id}")
            
            # Wait for generation with polling
            max_attempts = 30
            poll_interval = 2
            
            for attempt in range(max_attempts):
                logger.info(f"[DEBUG] Polling attempt {attempt + 1}/{max_attempts}")
                
                results_url = f"{self.leo_api_url}/generations/{generation_id}"
                results_response = requests.get(results_url, headers=self.leo_headers)
                
                if results_response.status_code == 200:
                    generation_data = results_response.json()
                    logger.info(f"[DEBUG] Generation response: {generation_data}")
                    
                    # Check if generation is complete
                    if generation_data.get('generations_by_pk', {}).get('status') == 'COMPLETE':
                        generated_images = generation_data.get('generations_by_pk', {}).get('generated_images', [])
                        if generated_images:
                            logger.info(f"[DEBUG] Successfully got {len(generated_images)} generated images")
                            return {
                                'status': 'success',
                                'image_url': generated_images[0]['url']
                            }
            
                await asyncio.sleep(poll_interval)
            
            return {
                'status': 'error',
                'error': 'Generation timed out or failed to complete'
            }
            
        except Exception as e:
            logger.error(f"[DEBUG] Error in generate_image: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }


    async def generate_image_with_reference(self, prompt: str, image_url: str, message_obj) -> Dict:
        """Generate image using Leonardo.ai with reference"""
        try:
            # Send processing message
            processing_message = await message_obj.reply_text(
                "🎨 Processing your reference image and generating new image...\n"
                "This might take a minute or two. Please wait..."
            )
            
            # Step 1: Get presigned URL and upload image
            upload_url = f"{self.leo_api_url}/init-image"
            payload = {"extension": "jpg"}
            
            logger.info("[DEBUG] Getting presigned URL for image upload")
            upload_response = requests.post(
                upload_url,
                headers=self.leo_headers,
                json=payload
            )
            
            if upload_response.status_code != 200:
                logger.error(f"[DEBUG] Failed to get presigned URL: {upload_response.text}")
                raise Exception("Failed to get presigned URL from Leonardo")
            
            # Parse upload data exactly as in their docs
            fields = json.loads(upload_response.json()['uploadInitImage']['fields'])
            url = upload_response.json()['uploadInitImage']['url']
            image_id = upload_response.json()['uploadInitImage']['id']
            
            logger.info(f"[DEBUG] Got image ID: {image_id}")
            
            # Get image from Telegram
            image_response = requests.get(image_url)
            if image_response.status_code != 200:
                raise Exception("Failed to download image from Telegram")
            
            
            files = {'file': ('image.jpg', image_response.content, 'image/jpeg')}
            s3_response = requests.post(url, data=fields, files=files)  
            
            if s3_response.status_code != 204:
                logger.error(f"[DEBUG] S3 upload failed with status {s3_response.status_code}")
                raise Exception("Failed to upload to S3")
            
            generation_url = f"{self.leo_api_url}/generations"
            payload = {
                "height": 512,
                "width": 1040,
                "modelId": "e71a1c2f-4f80-4800-934f-2c68979d8cc8", 
                "prompt": prompt,
                "photoReal": False,
                "init_image_id": image_id,
                "init_strength": 0.05,  
                "controlnets": [
                    {
                        "initImageId": image_id,
                        "initImageType": "UPLOADED",
                        "preprocessorId": 67,  # Style Reference
                        "strengthType": "Low"  
                    }
                ],
                "guidance_scale": 9,  
                "num_images": 1,
                "presetStyle": "DYNAMIC"  
            }
            
            logger.info(f"[DEBUG] Sending generation request with payload: {payload}")
            response = requests.post(generation_url, json=payload, headers=self.leo_headers)
            
            if response.status_code != 200:
                logger.error(f"[DEBUG] Generation failed: {response.text}")
                raise Exception(f"Generation failed with status {response.status_code}")
                
            generation_id = response.json()['sdGenerationJob']['generationId']
            logger.info(f"[DEBUG] Got generation ID: {generation_id}")
            
            
            time.sleep(20)  
            
            # Get the results
            results_url = f"{self.leo_api_url}/generations/{generation_id}"
            results_response = requests.get(results_url, headers=self.leo_headers)
            
            if results_response.status_code == 200:
                generated_images = results_response.json().get('generations_by_pk', {}).get('generated_images', [])
                if generated_images:
                    logger.info("[DEBUG] Successfully got generated image")
                    return {
                        'status': 'success',
                        'image_url': generated_images[0]['url']
                    }
            
            return {
                'status': 'error',
                'error': 'Failed to get generated image'
            }
            
        except Exception as e:
            logger.error(f"[DEBUG] Error in generate_image_with_reference: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel and end the conversation."""
        await update.message.reply_text(
            "Operation cancelled. Type /start to begin again.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

def main():
    """Run the bot."""
    # Create the bot instance
    bot = ContentGenerationBot()
    
    # Get the token from the environment variable
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        logger.error("No TELEGRAM_TOKEN found in environment variables")
        return

    # Create the Application
    application = ApplicationBuilder().token(token).build()

    # Create conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', bot.start)],
        states={
            States.INITIAL_PROMPT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_initial_prompt)
            ],
            States.CHOOSING_PROMPT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_prompt_choice)
            ],
            States.REFERENCE_CHOICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_reference_choice)
            ],
            States.AWAITING_REFERENCE: [
                MessageHandler(filters.PHOTO, bot.handle_reference_image)
            ],
            States.GENERATING_IMAGE: [
                MessageHandler(filters.ALL & ~filters.COMMAND, bot.start_image_generation)
            ],
            States.ITERATING_IMAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_image_iteration)
            ]
        },
        fallbacks=[CommandHandler('cancel', bot.cancel)]
    )

    # Add conversation handler to the application
    application.add_handler(conv_handler)

    # Start the Bot
    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
