import os
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

import torch
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    Trainer,
    TrainingArguments,
    DataCollatorForLanguageModeling,
)
from datasets import Dataset

@dataclass
class FineTuner:
    model_name_or_path: str
    output_dir: str
    train_data: List[Dict[str, str]]
    eval_data: Optional[List[Dict[str, str]]] = None
    tokenizer: Optional[Any] = field(init=False, default=None)
    model: Optional[Any] = field(init=False, default=None)
    training_args: Optional[TrainingArguments] = field(init=False, default=None)
    trainer: Optional[Trainer] = field(init=False, default=None)

    def __post_init__(self):
        self._prepare_environment()
        self._load_tokenizer_and_model()
        self._prepare_training_args()
        self._prepare_trainer()

    def _prepare_environment(self):
        os.makedirs(self.output_dir, exist_ok=True)
        if not torch.cuda.is_available():
            print("CUDA is not available. Training will be performed on CPU.")

    def _load_tokenizer_and_model(self):
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_name_or_path,
            use_fast=True,
            padding_side="left"
        )
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name_or_path
        )

        if self.tokenizer.pad_token is None:
            self.tokenizer.add_special_tokens({'pad_token': '[PAD]'})
            self.model.resize_token_embeddings(len(self.tokenizer))

    def _prepare_datasets(self):
        def tokenize_function(examples):
            return self.tokenizer(
                examples['prompt'],
                padding='max_length',
                truncation=True,
                max_length=512
            )

        train_dataset = Dataset.from_list(self.train_data)
        train_dataset = train_dataset.map(tokenize_function, batched=True)
        train_dataset.set_format(type='torch', columns=['input_ids', 'attention_mask'])

        eval_dataset = None
        if self.eval_data:
            eval_dataset = Dataset.from_list(self.eval_data)
            eval_dataset = eval_dataset.map(tokenize_function, batched=True)
            eval_dataset.set_format(type='torch', columns=['input_ids', 'attention_mask'])

        return train_dataset, eval_dataset

    def _prepare_training_args(self):
        self.training_args = TrainingArguments(
            output_dir=self.output_dir,
            overwrite_output_dir=True,
            num_train_epochs=3,
            per_device_train_batch_size=8,
            per_device_eval_batch_size=8,
            evaluation_strategy='steps' if self.eval_data else 'no',
            eval_steps=500 if self.eval_data else None,
            save_steps=500,
            logging_steps=100,
            learning_rate=5e-5,
            weight_decay=0.01,
            fp16=torch.cuda.is_available(),
            push_to_hub=False,
        )

    def _prepare_trainer(self):
        train_dataset, eval_dataset = self._prepare_datasets()
        data_collator = DataCollatorForLanguageModeling(
            tokenizer=self.tokenizer,
            mlm=False,
        )

        self.trainer = Trainer(
            model=self.model,
            args=self.training_args,
            data_collator=data_collator,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
        )

    def fine_tune(self):
        self.trainer.train()
        self.save_model()

    def save_model(self):
        self.trainer.save_model(self.output_dir)
        self.tokenizer.save_pretrained(self.output_dir)

    def generate(self, prompt: str, max_length: int = 50, num_return_sequences: int = 1):
        inputs = self.tokenizer(prompt, return_tensors='pt')
        inputs = {k: v.to(self.model.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_length=max_length,
                num_return_sequences=num_return_sequences,
                do_sample=True,
                top_p=0.95,
                top_k=60
            )
        return [self.tokenizer.decode(output, skip_special_tokens=True) for output in outputs]
