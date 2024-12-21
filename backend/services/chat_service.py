from openai import OpenAI
import json
from datetime import datetime
import re
import os
from enum import Enum
from typing import Dict, Any, Optional
from dotenv import load_dotenv
load_dotenv()

class ConversationState(Enum):
    INIT = "init"
    COLLECTING_EMAIL = "collecting_email"
    COLLECTING_PHONE = "collecting_phone"
    COLLECTING_DOB = "collecting_dob"
    COLLECTING_ADDRESS = "collecting_address"
    COLLECTING_LICENSE = "collecting_license"
    COLLECTING_LICENSE_NUMBER = "collecting_license_number"
    COLLECTING_TRANSMISSION = "collecting_transmission"
    COMPLETED = "completed"

class ChatService:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.conversations = {}
        self.system_prompt = """You are a friendly assistant helping with driving school registrations. Your role is to gather all the necessary information from students in a structured format. The details needed are: first name, last name, email, phone number, date of birth (YYYY-MM-DD), address, whether they currently hold a driving license (yes/no), their license number (if applicable), and their preferred type of transmission (automatic or manual). If the information provided is unorganized, identify and extract the required details. Keep the conversation engaging while ensuring you collect all the necessary data."""

    def _extract_fields_from_text(self, text: str) -> Dict[str, Any]:
        """Extract structured information from unstructured text using GPT-4"""
        prompt = f"""Extract the following fields from this text. Return only valid JSON:
        - firstName
        - lastName
        - email
        - phone
        - dateOfBirth (YYYY-MM-DD)
        - address
        - hasLicense (boolean)
        - licenseNumber (if license mentioned)
        - preferredTransmission (automatic/manual)

        Text: "{text}"
        
        Format the response as valid JSON. Only include fields that are clearly present in the text."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=500
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"Error extracting fields: {e}")
            return {}

    def _get_ai_response(self, conversation_history: list, current_state: ConversationState, missing_fields: list) -> str:
        """Get a contextual response from GPT-4 based on conversation history and missing fields"""
        messages = [
            {"role": "system", "content": self.system_prompt},
            *[{"role": "user" if i % 2 == 0 else "assistant", "content": msg} 
              for i, msg in enumerate(conversation_history)]
        ]
        
        prompt = f"""Current state: {current_state.value}
        Missing fields: {', '.join(missing_fields)}
        
        Provide, conversational response to collect the next piece of information.
        Keep it brief and focused on collecting the missing information."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[*messages, {"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=150
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error getting AI response: {e}")
            return f"Could you please provide your {missing_fields[0] if missing_fields else 'information'}?"

    def process_user_input(self, conversation_id: str, user_message: str) -> dict:
        # Initialize or get existing conversation
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = {
                "state": ConversationState.INIT,
                "collected_data": {},
                "history": []
            }
        
        conversation = self.conversations[conversation_id]
        conversation["history"].append(user_message)

        
        extracted_data = self._extract_fields_from_text(user_message)
        conversation["collected_data"].update(extracted_data)

       
        required_fields = ["firstName", "lastName", "email", "phone", "dateOfBirth", 
                         "address", "hasLicense", "preferredTransmission"]
        missing_fields = [field for field in required_fields 
                         if field not in conversation["collected_data"]]
        
        if "hasLicense" in conversation["collected_data"] and \
           conversation["collected_data"]["hasLicense"] and \
           "licenseNumber" not in conversation["collected_data"]:
            missing_fields.append("licenseNumber")

        if not missing_fields:
            conversation["state"] = ConversationState.COMPLETED
            ai_response = "Thank you! Your registration is complete."
        else:
            ai_response = self._get_ai_response(
                conversation["history"], 
                conversation["state"],
                missing_fields
            )

        conversation["history"].append(ai_response)
        
        return {
            "message": ai_response,
            "state": conversation["state"].value,
            "collected_data": conversation["collected_data"]
        }