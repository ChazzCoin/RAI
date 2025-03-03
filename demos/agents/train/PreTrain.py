import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments
from datasets import load_dataset, Dataset

class RaiTrain(Trainer):
    def compute_loss(self, model, inputs, return_outputs=False, num_items_in_batch=None):
        """
        Override compute_loss to ensure compatibility with the new trainer interface.
        """
        labels = inputs.pop("labels")
        outputs = model(**inputs)
        logits = outputs.get("logits")

        # Calculate loss (example for classification task)
        loss_fn = torch.nn.CrossEntropyLoss()
        loss = loss_fn(logits.view(-1, logits.size(-1)), labels.view(-1))

        return (loss, outputs) if return_outputs else loss

class HuggingFaceTrainer:
    def __init__(self, model_name_or_path, output_dir="./output", tokenizer_name_or_path=None):
        self.model_name_or_path = model_name_or_path
        self.output_dir = output_dir
        self.tokenizer_name_or_path = tokenizer_name_or_path or model_name_or_path

        # Load model and tokenizer
        self.model = AutoModelForCausalLM.from_pretrained(self.model_name_or_path)
        self.tokenizer = AutoTokenizer.from_pretrained(self.tokenizer_name_or_path)
        # Check if the tokenizer has a pad_token, and add one if it doesn't
        if self.tokenizer.pad_token is None:
            self.tokenizer.add_special_tokens({'pad_token': '[PAD]'})
            self.model.resize_token_embeddings(len(self.tokenizer))

    def preprocess_dataset(self, dataset_path, text_column="text", max_length=512):
        dataset = load_dataset(dataset_path)

        def tokenize_function(examples):
            inputs = self.tokenizer(
                examples[text_column],
                truncation=True,
                padding="max_length",
                max_length=max_length,
            )
            inputs["labels"] = inputs["input_ids"].copy()
            return inputs
        tokenized_dataset = dataset.map(tokenize_function, batched=True, remove_columns=[text_column])
        return tokenized_dataset

    def pre_train(self, tokenized_dataset, num_epochs=3):
        # Prepare training arguments
        training_args = TrainingArguments(
            output_dir=self.output_dir,
            per_device_train_batch_size=4,
            gradient_accumulation_steps=8,
            num_train_epochs=num_epochs,
            save_steps=1000,
            save_total_limit=2,
            learning_rate=5e-5,
            logging_dir=f"{self.output_dir}/logs",
            logging_steps=500,
            report_to="tensorboard",
            eval_strategy="steps",
            eval_steps=500,
            load_best_model_at_end=True,
            save_strategy="steps",
            fp16=False,  # Disable mixed precision
        )

        train_test_split = tokenized_dataset["train"].train_test_split(test_size=0.2)
        train_dataset = train_test_split["train"]
        eval_dataset = train_test_split["test"]
        # Initialize Trainer with custom loss computation
        trainer = RaiTrain(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
        )
        trainer.train()

        # Save the final model
        self.model.save_pretrained(self.output_dir)
        self.tokenizer.save_pretrained(self.output_dir)

    def load_model(self):
        self.model = AutoModelForCausalLM.from_pretrained(self.output_dir)
        self.tokenizer = AutoTokenizer.from_pretrained(self.output_dir)


# Example Usage
if __name__ == "__main__":
    pretrainer = HuggingFaceTrainer(model_name_or_path="openai-community/gpt2-xl", output_dir="checkpoints-gpt2-xl")
    dataset_path = "/Users/chazzromeo/Desktop/pcsc2024/test"
    tokenized_data = pretrainer.preprocess_dataset(dataset_path=dataset_path)
    # Train the model with the tokenized dataset
    pretrainer.pre_train(tokenized_dataset=tokenized_data, num_epochs=1)
