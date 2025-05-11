API_KEY = ''
PROMT = """
Determine if there are any dishes/foods/drinks here. If so, write the answer in Russian in the format: names of all dishes in the photo with a capital letter separated by commas and then in parentheses each ingredient you see in these dishes.
Determine the total across all food products in the photo:
Calories: int
Protein: float grams (int%)
Fat: float grams (int%)
Carbohydrates: float grams (int%) – float carbohydrate exchanges  (Be very careful to calculate this position! If the product is processed (e.g. boiled, fried), please take this into account when calculating!)
Total weight: int grams.
Glycemic index: float (int%)

Calculate as accurately as possible.

If the product contains proteins and fats, write: Attention! The product contains protein-fat units. Depending on the total amount of fatty food, additional compensation for proteins and fats may be required after 2-3 hours!

Calculate protein-fat units: float g (int%) – float units in protein-fat units.

To understand protein-fat units (PFUs) - learn from this example:

Suppose we have a pizza, and the box indicates the amount of proteins, fats, and carbohydrates. The whole pizza contains 858 kcal and 107.6 g of carbohydrates. To calculate the number of kilocalories that these carbohydrates will give us, we need to do 107.6 × 4 (assuming that 1 g of carbohydrates converts to 4 kcal of energy), which equals 430.4 kcal.

Now, let's find out how many kilocalories the proteins and fats will give us: 858 (total kcal in the whole pizza) - 430.4 (number of kcal for carbohydrates that we calculated) = 427.6 kcal.

Finally, we divide the resulting number of kilocalories by 100 (because 1 PFU equals 100 kcal): 427.6 / 100 = 4.3. Thus, we find that the whole pizza contains 4.3 PFUs.

Then write: Enjoy your meal!

If, while analyzing the food, you discovered protein-fat units in their composition, then send another message with the following text in 2 hours: Обратите внимание, пища, которую вы приняли 2 часа назад содержала белково-жировые единицы БЖЕ, проверьте уровень сахара в крови - возможно, необходима дополнительная компенсация!

Remember that “carbohydrate exchanges” in Russian is “Хлебные единицы (ХЕ)», а «PFUs” - “(БЖЕ)»!
"""
