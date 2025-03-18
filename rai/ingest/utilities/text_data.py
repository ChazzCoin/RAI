
gpt4_test = """
 Take the following custom python class I have built and create a new class that inherits this one and does the following.
 
 1. Takes in a 'prefix' and then is able to manage and browse.py documents.
 2. Base functions for get all documents. get document by id. delete document. update document.
 
 
 class ChromaClient:
    def __init__(self, host=CHROMA_HTTP_HOST, port=CHROMA_HTTP_PORT):

        if CHROMA_HTTP_HOST == "local":
            Log.w("\n--Chroma PersistentClient--\n")
            self.client = chromadb.PersistentClient(
                tenant=chromadb.DEFAULT_TENANT,
                database=chromadb.DEFAULT_DATABASE,
            )
            Log.s("Successfully Connected to Local Chromadb Client.")
        else:
            Log.w("\n--Chroma HttpClient--\n")
            self.client = chromadb.HttpClient(
                host=host,
                port=port,
                headers=CHROMA_HTTP_HEADERS,
                ssl=CHROMA_HTTP_SSL,
                tenant=chromadb.DEFAULT_TENANT,
                database=chromadb.DEFAULT_DATABASE,
                settings=Settings(allow_reset=True, anonymized_telemetry=False),
            )
            Log.w("Chroma Host:", CHROMA_HTTP_HOST)
            Log.w("Chroma Port:", CHROMA_HTTP_PORT)
            Log.w("Chroma Database:", CHROMA_DATABASE)
            Log.w("Chroma Tenant:", CHROMA_TENANT)
            Log.s("Successfully Connected to Remote Chromadb Client.")

    def get_all_collections_by_chain(self, *collection_paths: str):
        try:
            def chain_collection_names(*collection_names: str):
                collection_name = ""
                index = 0
                for c in collection_names:
                    if index == 0:
                        collection_name = c
                    else:
                        collection_name = f"{collection_name}.{c}"
                    index += 1
                return collection_name

            # Assuming you have a ChromaDB client instance named 'VECTOR_DB_CLIENT'
            collections = self.client.list_collections()
            collection_names = [collection.name for collection in collections]

            base_path = chain_collection_names(*collection_paths)
            # Filter by prefix if provided
            final_names = [col for col in collection_names if col.startswith(base_path)]

            return final_names

        except Exception as e:
            # Log error with proper context
            Log.e(f"Error retrieving collections from ChromaDB: {e}")
            return []

    def has_collection(self, collection_name: str) -> bool:
        # Check if the collection exists based on the collection name.
        collections = self.client.list_collections()
        return collection_name in [collection.name for collection in collections]

    def delete_collection(self, collection_name: str):
        # Delete the collection based on the collection name.
        return self.client.delete_collection(name=collection_name)

    def search_text(self, collection_name: str, texts: list[str], limit: int) -> Optional[SearchResult]:
        collection = self.client.get_collection(name=collection_name)
        if collection:
            result = collection.query(
                query_texts=texts,
                n_results=limit,
            )

            return SearchResult(
                **{
                    "ids": result["ids"],
                    "distances": result["distances"],
                    "documents": result["documents"],
                    "metadatas": result["metadatas"],
                }
            )
        return None
    def search_vector(self, collection_name: str, vectors: list[list[float]], limit: int, where:dict=None) -> Optional[SearchResult]:
        # Search for the nearest neighbor items based on the vectors and return 'limit' number of results.
        collection = self.client.get_collection(name=collection_name)
        if collection:

            if not where:
                result = collection.query(
                    query_embeddings=vectors,
                    n_results=limit,
                )
            else:
                result = collection.query(
                    query_embeddings=vectors,
                    n_results=limit,
                    where=where,
                )

            return SearchResult(
                **{
                    "ids": result["ids"],
                    "distances": result["distances"],
                    "documents": result["documents"],
                    "metadatas": result["metadatas"],
                }
            )
        return None

    def get(self, collection_name: str) -> Optional[GetResult]:
        # Get all the items in the collection.
        collection = self.client.get_collection(name=collection_name)
        if collection:
            result = collection.get()
            return GetResult(
                **{
                    "ids": [result["ids"]],
                    "documents": [result["documents"]],
                    "metadatas": [result["metadatas"]],
                }
            )
        return None

    def insert(self, collection_name: str, items: list[VectorItem]):
        # Insert the items into the collection, if the collection does not exist, it will be created.
        collection = self.client.get_or_create_collection(name=collection_name)

        ids = [item["id"] for item in items]
        documents = [item["text"] for item in items]
        embeddings = [item["vector"] for item in items]
        metadatas = [item["metadata"] for item in items]

        batches = create_batches(
            api=self.client,
            documents=documents,
            embeddings=embeddings,
            ids=ids,
            metadatas=metadatas,
        )
        for batch in tqdm(batches, f"Inserting into [ {collection_name} ]", colour="green"):
            collection.add(*batch)
        Log.s(f"Added {len(batches)} batched document(s) into Chroma Collection:", collection_name)

    def upsert(self, collection_name: str, items: list[VectorItem]):
        # Update the items in the collection, if the items are not present, insert them. If the collection does not exist, it will be created.
        collection = self.client.get_or_create_collection(name=collection_name)

        ids = [item["id"] for item in items]
        documents = [item["text"] for item in items]
        embeddings = [item["vector"] for item in items]
        metadatas = [item["metadata"] for item in items]

        collection.upsert(
            ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas
        )

    def delete(self, collection_name: str, ids: list[str]):
        # Delete the items from the collection based on the ids.
        collection = self.client.get_collection(name=collection_name)
        if collection:
            collection.delete(ids=ids)

    def reset(self):
        # Resets the database. This will delete all collections and item entries.
        return self.client.reset()



"""



schedule_text = """


PARK CITY SOCCER CLUB 2024/25 

An overview of a year-round competitive soccer team experience

 

Placement results are posted to the Club website by the end of the second day after tryouts.

Preliminary teams are named for 2016/U9s, with an extended tryout during July resulting in

final team assignments by early August. 

 

ATHLETE / FAMILY COMMITMENT AND EXPECTATIONS

The mission of the Park City Soccer Club is to build community through whole athlete development and a passionate pursuit of excellence both on and off the pitch. In addition to individual development, it is also imperative that athletes and families understand the commitment they are making to the team, each other, and the Park City Soccer Club. Attendance at all team functions is expected, however it is understood that at times a conflict may arise. PCSC supports multi-sport/multi-activity athletes and recognizes that at times additional endeavors may coincide with Club and team events. In the event of a scheduling conflict, please discuss with your coach.

 

Our program runs on people! Athletes, coaches, parents, and community members are critical to the club athlete experience. Consistent involvement of the athlete ensures a more meaningful experience for all. Everyone will find a chance to participate in the program’s success. Whether it’s helping out the Park City Soccer Club’s own Extreme Cup, working to make your individual team run smoothly, or lending your talents at the wider club level; Park City Soccer Club is grateful for your involvement.

Contact: Joel Person at joelp@gmail.com or 205-555-5555
 

SUMMER

* JUNE 3-5 *: Team Kickoff Meetings at the PC Hospital - Blair Education Center - In-person only.

Families meet coaches and team members. Team annual plan, PlayMetrics, and uniforms will be discussed along with coaches’ philosophy, tournaments, and more.

JUNE 10-21: Open Play/Functional Training will be available for 2011-2016 teams.

JUNE 24-28: One.Soccer Camp (optional, requires additional fee.)

JUNE 29: The PCSC’s education series with Athletic Republic kicks off.

JULY 8-20: Pool play (age group) training begins for 2011-2016 teams.

JULY 19-21: Team and age specific Kickoff Camps: There will be three days of training, scrimmages, strategy, and social gatherings in preparation for Park City’s Extreme Cup tournament and the 2024/25 season. Attendance is highly encouraged.

JULY 25-27:  Annual Park City Extreme Cup Tournament

All PCSC teams are expected to play. Games will take place in Park City and various fields in the Wasatch Back. Each team should plan to play 3-4 games Thursday-Saturday. There are many opportunities for volunteer involvement before, during, and after the event. 

AUGUST: Team training 2x per week in preparation for the fall season. Most teams will participate in an August tournament. Club-wide BBQ & potluck August 17.

 

FALL

AUGUST 19-OCTOBER: Fall League Play: 7-10 games with home games in Park City, and away games taking place along the Wasatch Front. Training continues 2x per week.

NOVEMBER-DECEMBER: Many teams will compete in a tournament. Most teams will wrap up the season with social events, team bonding opportunities, and player reviews. Functional/Pool play training will also be offered.

 

WINTER

JANUARY-FEBRUARY: Team training resumes 1-2x per week.

Futsal League (optional) begins in Heber with 2 games per week. Play ends in February.

 

SPRING

MARCH: Team training ramps up to 2x per week in preparation for spring season.

MARCH 16-MAY: Spring League Play: 7-10 games with home games in Park City, and away games taking place along the Wasatch Front. Training continues 2x per week during the season. Many teams participate in a May tournament.

PLAYER PLACEMENTS for the 2025/2026 season will take place at the end of May.

 

TOURNAMENTS

Tournaments, whether it’s a local or a destination event, are excellent opportunities for development and team building. Attending events as a team is a large part of the PCSC experience. There are additional fees for tournaments and travel costs; scholarship support is available for travel tournaments. The calendar is set for the 2024/25 season as follows:  Click here for team tournaments.

Park City Soccer Club
6443 N Business Park Loop, Suite K
Park City, UT 84098
Phone: 435.901.3715
www.parkcitysoccer.org


More information is located in the Parent and Player’s Handbooks: Click Here

﻿

For questions, please contact PCSC Executive Director Shelley Gillwald at: sgillwald@parkcitysoccer.org

"""


book_text = """
Isaac Newton’s amazing genius continues
to significantly influence our lives
today. His discoveries regarding the
Laws of Motion and the Law of Universal
Gravity literally changed the way humans
view the world around us and formed the
basis for modern physics. He built the first
practical reflector telescope and using a
prism, also proved that white light is made
up of a spectrum of light (colors mixed
together), rather than being a separate
color itself, as previously believed. His
Method of Fluxions became the foundation
for differential calculus, which is applied
extensively in many fields today, from
designing factories to determining the rate of
a chemical reaction.
Isaac Newton grew up on a farm in rural
England. As a boy, he completely immersed
himself in the study and application of a
book entitled The Mysteries of Nature and
Art, building various mechanical devices
and discovering other ways to investigate
the world around him. Later, when he was
a student at the University of Cambridge,
the Great Plague of London (1665-1667)
broke out and all the students were sent
home. Newton returned to the farm where
he continued his passionate exploration of
the natural world. This period of study
and reflection and later time spent on his
farm were immensely fruitful for Newton,
providing insights into some of his most
important discoveries.
While a great deal of information has
been widely available regarding other aspects
of Isaac Newton’s life and work, until
recently
very little
was generally
known regarding his
deep passion for mysticism
and Alchemy, even though he
wrote more than one million words on
the subject! Rosicrucians, however, have
been aware of Sir Isaac Newton’s mystical
interests for centuries.
At the time of his death, Isaac Newton’s
personal library contained around 1,800
volumes, including 169 books on the
topic of alchemy. His was considered one
of the most important alchemical libraries
in the world. His collection also included a
thoroughly annotated personal copy of The
Fame and Confession of the Fraternity Rosie
Cross, by Thomas Vaughan—the English
translation of the Rosicrucian Manifestos.
He also possessed copies of Themis Aurea
(Themis Aurea: The Laws of the Fraternity
of the Rosie Cross) and Symbola Aurea
Mensae Duodecim Nationum, important
books related to Rosicrucianism,
written by the Rosicrucian defender and
Alchemist, Michael Maier. These books
were all extensively annotated by Newton.
Isaac Newton chose to keep his
mystical interests secret. There would
have been many good reasons for doing so
during the age in which he lived. At that
time, the English Crown had outlawed
Page 51
certain Alchemical practices, for example,
creating gold through alchemical processes,
because they feared that it might devalue
the British currency. The penalty for this
crime was death by hanging. Newton
also faced certain scrutiny from his peers
within the scientific community. Newton
was repeatedly challenged throughout his
lifetime regarding his theories and these
confrontations deeply disturbed him.
Newton also felt that he was protecting
humanity from those who might misuse
alchemical knowledge. In a letter to fellow
Alchemist Robert Boyle, one of the leading
intellectual figures of the seventeenth
century and largely regarded today as the
first modern Chemist, Newton urged
Boyle to keep “high silence” in discussing
the principles of Alchemy publicly. He
wrote that these principles “may possibly
be an inlet to something more noble
that is not to be communicated without
immense damage to the world…There are
other things besides the transmutation of
metals which none but they [the Hermetic
writers] understand.”1
Even after his Alchemical manuscripts
were discovered after his death, they were
misunderstood. Although Newton served
as the President of the Royal Society for
twenty-four years, following his death
in 1727, they decided that his papers on
Alchemy were “not fit to be printed.” They
remained largely unknown for the next
200 years.
Fortunately many of his previously
unavailable manuscripts were donated to
King’s College Library at the University
of Cambridge in 1946, as a bequest from
the British economist John Maynard
Keynes, who had purchased them from
one of Newton’s relatives in 1936. These
texts include Newton’s extensive notes and
diagrams related to his alchemical research
and experiments over several decades.
Many of them include alchemical code,
such as alchemical symbols (for example,
☾, symbolizing silver, Monday, and the
Moon), alchemical phrases (such as “the
Green Lion,” which typically represents
the essence of a metal or the raw forces of
nature), and using ancient mythology to
describe alchemical processes (for example,
in the language of Alchemy, the deities
Venus, Mars, and Vulcan represent copper,
iron, and fire).
Jed Buchwald, with the California
Institute of Technology, states, “There
was a profound element to the practice of
alchemy which really makes it deserving
of being called early modern chemistry.
Newton’s not a madman playing around
with strange spirituous substances, he’s
trying to actually figure out how to change
material particles around to get one thing
out of something else. And that’s not so
weird.”2
In his text entitled, “Newton, the
Man,” Keynes, a great admirer of Newton
and well-acquainted with his work, states:
There are an unusual number of
manuscripts of the early English
alchemists in the libraries of
Cambridge. It may be that there was
some continuous esoteric tradition
within the University which sprang into
activity again in the twenty years from
1650 to 1670. At any rate, Newton was
clearly an unbridled addict. It is this
with which he occupied “about 6 weeks
at spring and 6 at the fall when the fire
in the laboratory scarcely went out” at
the very years when he was composing
the Prinicipia—and about which he
told Humphrey Newton [his assistant]
not a word. Moreover, he was almost
entirely concerned, not in serious
experiment, but in trying to read the
riddle of tradition, to find meaning in
cryptic verses, to imitate the alleged but
largely imaginary experiments of the
initiates of past centuries.
"""