from rai.assistant.ai_models import AiModels
from rai.base.BaseTextAgents.BaseTextAgent import RaiBaseTextAgent
from rai.data.DataLoadIn import DataBaseProcessor


class DataProcessorAgent(DataBaseProcessor):
    results = []

    def __init__(self, prefix=None, output_file=None, output_type='json', input_file=None):
        super().__init__(prefix, output_file, output_type, input_file)

    def generate_faq(self):
        data = self.get_cleaned_data()

        for item in data:
            if self.is_within_model_token_limit(text=item, model=AiModels.DEFAULT_OPENAI):
                try:
                    qas = RaiBaseTextAgent.generate(name="faq", user_prompt=item)
                    # if pipeline returns a string or empty, skip
                    if isinstance(qas, str) or not qas:
                        continue
                    if qas.results:
                        for i in qas.results:
                            self.to_save_data.append({ "question": i.question, "answer": i.answer })
                            # Immediately save to file after adding
                            self.json_writer()
                except Exception as e:
                    print(e)
                    continue
            else:
                # If text is too large, split and process in segments
                item_split = self.split_text_to_paragraphs(text=item)
                for isplit in item_split:
                    try:
                        qas = RaiBaseTextAgent.generate(name="faq", user_prompt=isplit)
                        if isinstance(qas, str) or not qas:
                            continue
                        if qas.results:
                            for i in qas.results:
                                self.to_save_data.append({"question": i.question, "answer": i.answer})
                                # Immediately save to file after adding
                                self.json_writer()
                    except Exception as e:
                        print(e)
                        continue

        print("Finished.")

    def convert_faq_to_finetune_format(self, system_prompt):
        for item in self.raw_data:
            question = item.get("question", "")
            answer = item.get("answer", "")

            # Construct the new format
            new_entry = {
                "messages": [
                    {"role": "system", "content": system_prompt },
                    {"role": "user", "content": self.TEXT_CLEANER(question)},
                    {"role": "assistant", "content": self.TEXT_CLEANER(answer)},
                ]
            }
            self.to_save_data.append(new_entry)
            self.jsonl_single_writer(new_entry)
        return self.to_save_data



if __name__ == '__main__':
    pcsc2024_sys_prompt = (
        "You are a highly knowledgeable, retrieval-augmented AI Assistant specializing "
        "in answering questions about the Park City Soccer Club. You have relevant data "
        "on the club's policies, training guidelines, age-group objectives, schedules, "
        "and any other official information. Provide thorough, accurate, and helpful "
        "answers to any inquiries related to Park City Soccer Club. If you are unsure "
        "of the correct response, provide partial information and clarify that it is "
        "your best understanding with limited data."
    )
    file_name = f"/Users/chazzromeo/Desktop/pcsc2024/ready_to_train/faq_January 13 2025.json"
    out = f"/Users/chazzromeo/Desktop/pcsc2024/ready_to_train/fine_tune_faq_January 13 2025.json"
    agent = DataProcessorAgent(output_file=out, input_file=file_name)
    agent.convert_faq_to_finetune_format(pcsc2024_sys_prompt)
