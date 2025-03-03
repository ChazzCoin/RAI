from transformers import AutoModelForCausalLM, AutoTokenizer


def generate_text_from_checkpoint(
        prompt,
        checkpoint_folder,
        max_length=50,
        temperature=0.1,
        top_k=50,
        top_p=0.9
):
    """
    Generate text using a custom model checkpoint.

    :param prompt: The input prompt for text generation.
    :param checkpoint_folder: Path to the folder containing the saved model and tokenizer.
    :param max_length: Maximum length of the generated text.
    :param temperature: Sampling temperature; higher values generate more diverse text.
    :param top_k: The number of highest probability vocabulary tokens to keep for top-k filtering.
    :param top_p: Cumulative probability threshold for nucleus sampling.
    :return: The generated text.
    """
    try:
        # Load the model and tokenizer
        model = AutoModelForCausalLM.from_pretrained(checkpoint_folder)
        tokenizer = AutoTokenizer.from_pretrained(checkpoint_folder)

        # Ensure tokenizer has a padding token
        if tokenizer.pad_token is None:
            tokenizer.add_special_tokens({'pad_token': '[PAD]'})
            model.resize_token_embeddings(len(tokenizer))

        # Encode the input prompt
        inputs = tokenizer(prompt, return_tensors="pt")

        # Generate text
        output_ids = model.tool(
            inputs["input_ids"],
            max_length=max_length,
            temperature=temperature,
            top_k=top_k,
            top_p=top_p,
            no_repeat_ngram_size=1,
            num_return_sequences=1
        )

        # Decode the generated text
        generated_text = tokenizer.decode(output_ids[0], skip_special_tokens=True)
        return generated_text

    except Exception as e:
        return f"An error occurred: {str(e)}"


# Example usage
if __name__ == "__main__":
    prompt = "Children do not learn in the same way as adults especially when the learning process involves "
    prompt2 = "PCSC Individual Development Plan"
    checkpoint_folder = "./checkpoints-gpt2-xl"  # Replace with your folder path
    generated_text = generate_text_from_checkpoint(prompt2, checkpoint_folder)
    print("Generated Text:", generated_text)
