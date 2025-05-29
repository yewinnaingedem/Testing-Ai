# from sklearn.feature_extraction.text import TfidfVectorizer
# # import pyidaungsu as pds
# from sklearn.model_selection import train_test_split
# from sklearn.linear_model import LogisticRegression
# from sklearn.metrics import accuracy_score

# seat_viewing_datasets = [
#     ("ငါကြည့်ချင်တယ်", 1),  
#     ("မကြည့်ချင်ဘူး။", 0),  
#     ("ငါဒီပစ္စည်းကိုဝယ်ချင်တယ်။", 1)   ,
#     ("ထိုင်ခုံအစီအစဥ်ကြည့်မယ်။", 1)   ,
#     ("အခြားလမ်းကြောင်းရှိနိုင်ပါသလား။", 0)   ,
#     ("ငါနည်းနည်းကြည့်မယ်။", 1)   ,
#     ("ငါရွေးချယ်ခွင့်ရှိနိုင်မလား။", 1)   ,
#     ("ငါရွေးမယ်။", 1)   ,
#     ("ပိုကောင်းတဲ့ထိုင်ခုံရချင်တယ်။", 1)   ,
#     ("မယူချင်ဘူး။",  0)   ,
#     ("ငါဒီပစ္စည်းကိုမဝယ်ချင်တယ်။", 0)   ,
#     ("မကြိုက်ဘူး။", 0)   ,
#     ("ဈေးကြီးတယ်။", 0 )   ,
#     ("သိပ်မဆိုးပါဘူး။", 1)   ,
#     ("Yes", 1)   ,
#     ("Okay", 1)   ,
#     ("ငါ စိတ်မဝင်စားဘူး။" , 0) ,
#     ("No", 0) ,
#     ("I would like to view the seat plan", 1) ,
#     ("I would like to buy the another route", 0) ,
#     ("another route", 0) ,
#     ("I don't want it", 0) ,
#     ("I don't like it", 0) ,
# ]

# sentences, labels = zip(*seat_viewing_datasets)

# # tokenized_corpus = [pds.tokenize(sentence) for sentence in sentences]

# processed_corpus = [" ".join(tokens) for tokens in tokenized_corpus]

# vectorizer = TfidfVectorizer()
# X = vectorizer.fit_transform(processed_corpus)

# # print("TF-IDF Matrix:\n", X.toarray())

# # Split data into training and testing sets
# X_train, X_test, y_train, y_test = train_test_split(X, labels , test_size=0.2, random_state=42)

# # Train the classifier
# model = LogisticRegression()
# model.fit(X_train, y_train)

# # Predict on test data
# y_pred = model.predict(X_test)

# # Evaluate the model
# accuracy = accuracy_score(y_test, y_pred)

# def load_stopwords_from_file(file_path = "/home/yewinnaing/Ai-Training/research/words/stop_words.txt"):
#     with open(file_path, "r", encoding="utf-8") as file:
#         stopwords = [line.strip() for line in file]
#     return stopwords
 
# def seat_view_predition(input) :
#     input = pds.cvt2zg(input) 
#     new_tokens = pds.tokenize(input , form="word")
#     myanmar_stopwords = load_stopwords_from_file() 
#     new_tokens = [word for word in new_tokens if word not in myanmar_stopwords]
#     new_processed = " ".join(new_tokens)
#     new_features = vectorizer.transform([new_processed])
#     prediction = model.predict(new_features)
#     return prediction[0]

