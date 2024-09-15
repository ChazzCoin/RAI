import re, subprocess

"""
content = re.sub(r'\s\sredis.', r'  await redis.', content)
content = re.sub(r'\s\smodels\.', r'  return models.', content)
content = re.sub(r'=\smodels\.', r'= await models.', content)
//
content = re.sub(r'\s\sawait models\.', r'  return models.', content)
"""

sequelize_import_name = "sequelize"

SEQUELIZEs_one = [
    [r'\'\$ne\'', rf'[{sequelize_import_name}.Op.ne]'],
    [r'\'\$eq\'', rf'[{sequelize_import_name}.Op.eq]'],
    [r'\'\$gte\'', rf'[{sequelize_import_name}.Op.gte]'],
    [r'\'\$gt\'', rf'[{sequelize_import_name}.Op.gt]'],
    [r'\'\$lte\'', rf'[{sequelize_import_name}.Op.lte]'],
    [r'\'\$lt\'', rf'[{sequelize_import_name}.Op.lt]'],
    [r'\'\$not\'', rf'[{sequelize_import_name}.Op.not]'],
    [r'\'\$is\'', rf'[{sequelize_import_name}.Op.is]'],
    [r'\'\$and\'', rf'[{sequelize_import_name}.Op.and]'],
    [r'\'\$or\'', rf'[{sequelize_import_name}.Op.or]'],
    [r'\'\$in\'', rf'[{sequelize_import_name}.Op.in]'],
    [r'\'\$notIn\'', rf'[{sequelize_import_name}.Op.notIn]'],
    [r'\'\$like\'', rf'[{sequelize_import_name}.Op.like]'],
    [r'\'\$notLike\'', rf'[{sequelize_import_name}.Op.notLike]'],
    [r'\'\$iLike\'', rf'[{sequelize_import_name}.Op.iLike]'],
    [r'\'\$notILike\'', rf'[{sequelize_import_name}.Op.notILike]'],
    [r'\'\$regexp\'', rf'[{sequelize_import_name}.Op.regexp]'],
    [r'\'\$notRegexp\'', rf'[{sequelize_import_name}.Op.notRegexp]'],
    [r'\'\$iRegexp\'', rf'[{sequelize_import_name}.Op.iRegexp]'],
    [r'\'\$notIRegexp\'', rf'[{sequelize_import_name}.Op.notIRegexp]'],
    [r'\'\$between\'', rf'[{sequelize_import_name}.Op.between]'],
    [r'\'\$notBetween\'', rf'[{sequelize_import_name}.Op.notBetween]'],
    [r'\'\$overlap\'', rf'[{sequelize_import_name}.Op.overlap]'],
    [r'\'\$contains\'', rf'[{sequelize_import_name}.Op.contains]'],
    [r'\'\$contained\'', rf'[{sequelize_import_name}.Op.contained]'],
    [r'\'\$adjacent\'', rf'[{sequelize_import_name}.Op.adjacent]'],
    [r'\'\$strictLeft\'', rf'[{sequelize_import_name}.Op.strictLeft]'],
    [r'\'\$strictRight\'', rf'[{sequelize_import_name}.Op.strictRight]'],
    [r'\'\$noExtendRight\'', rf'[{sequelize_import_name}.Op.noExtendRight]'],
    [r'\'\$noExtendLeft\'', rf'[{sequelize_import_name}.Op.noExtendLeft]'],
    [r'\'\$any\'', rf'[{sequelize_import_name}.Op.any]'],
    [r'\'\$all\'', rf'[{sequelize_import_name}.Op.all]'],

]
SEQUELIZEs = [
    [r'\$ne\'', rf'[{sequelize_import_name}.Op.ne]'],
    [r'\$eq', rf'[{sequelize_import_name}.Op.eq]'],
    [r'\$gte', rf'[{sequelize_import_name}.Op.gte]'],
    [r'\$gt', rf'[{sequelize_import_name}.Op.gt]'],
    [r'\$lte', rf'[{sequelize_import_name}.Op.lte]'],
    [r'\$lt', rf'[{sequelize_import_name}.Op.lt]'],
    [r'\$not', rf'[{sequelize_import_name}.Op.not]'],
    [r'\$is', rf'[{sequelize_import_name}.Op.is]'],
    [r'\$and', rf'[{sequelize_import_name}.Op.and]'],
    [r'\$or', rf'[{sequelize_import_name}.Op.or]'],
    [r'\$in\'', rf'[{sequelize_import_name}.Op.in]'],
    [r'\$notIn', rf'[{sequelize_import_name}.Op.notIn]'],
    [r'\$like', rf'[{sequelize_import_name}.Op.like]'],
    [r'\$notLike', rf'[{sequelize_import_name}.Op.notLike]'],
    [r'\$iLike', rf'[{sequelize_import_name}.Op.iLike]'],
    [r'\$notILike', rf'[{sequelize_import_name}.Op.notILike]'],
    [r'\$regexp', rf'[{sequelize_import_name}.Op.regexp]'],
    [r'\$notRegexp', rf'[{sequelize_import_name}.Op.notRegexp]'],
    [r'\$iRegexp', rf'[{sequelize_import_name}.Op.iRegexp]'],
    [r'\$notIRegexp', rf'[{sequelize_import_name}.Op.notIRegexp]'],
    [r'\$between', rf'[{sequelize_import_name}.Op.between]'],
    [r'\$notBetween', rf'[{sequelize_import_name}.Op.notBetween]'],
    [r'\$overlap', rf'[{sequelize_import_name}.Op.overlap]'],
    [r'\$contains', rf'[{sequelize_import_name}.Op.contains]'],
    [r'\$contained', rf'[{sequelize_import_name}.Op.contained]'],
    [r'\$adjacent', rf'[{sequelize_import_name}.Op.adjacent]'],
    [r'\$strictLeft', rf'[{sequelize_import_name}.Op.strictLeft]'],
    [r'\$strictRight', rf'[{sequelize_import_name}.Op.strictRight]'],
    [r'\$noExtendRight', rf'[{sequelize_import_name}.Op.noExtendRight]'],
    [r'\$noExtendLeft', rf'[{sequelize_import_name}.Op.noExtendLeft]'],
    [r'\$any', rf'[{sequelize_import_name}.Op.any]'],
    [r'\$all', rf'[{sequelize_import_name}.Op.all]'],
]

GLOBALs = [
    [r'\s\sredis\.', r'  await redis.'],
    [r'\s\smodels\.', r'  return models.'],
    [r'=\smodels\.', r'= await models.'],
    [r'\s\scb\(', r'  return cb('],
    [r'\s\scallback\(', r'  return callback('],
    [r'\s\sseriesCallback\(', r'  return seriesCallback('],
    [r'\s\scb\(', r'  return cb('],
    [r'\s\scallback_fn\(', r'  return callback_fn('],
    [r'\s\swaterfallcallback\(', r'  return waterfallcallback('],
    [r'await callback\(', r'return callback('],
    [r'\s\snotify\.', r'  await notify.'],
    [r'\s\sawait\sasync\.', r'  async.'],
    [r'\s\sres\.', r'  return res.']
]
ADD_AWAIT_TO = [
    "self",
    "ApptFnObj",
    "RideFunction"
]
ADD_RETURN_TO = [
    "res",
    f"this\."
    "fuseObj"
]

def open_file(file) -> str:
    with open(file, 'r', encoding='utf-8') as file:
        return file.read()
def save_file(file, content):
    with open(file, 'w', encoding='utf-8') as file:
        file.write(content)

def run_globals(file_path):
    content = open_file(file_path)
    # Globals
    for reg in GLOBALs:
        content = re.sub(reg[0], reg[1], content)
    save_file(file_path, content)

def run_sequelizer(file_path):
    content = open_file(file_path)
    # Globals
    for reg in SEQUELIZEs_one:
        content = re.sub(reg[0], reg[1], content)
    for reg in SEQUELIZEs:
        content = re.sub(reg[0], reg[1], content)
    save_file(file_path, content)
def add_return_to_response(file_path):
    content = open_file(file_path)
    for add_r_to in ADD_RETURN_TO:
        content = re.sub(rf'\s\s{add_r_to}\.', rf'  return {add_r_to}.', content)
    save_file(file_path, content)

def add_return_to_callbacks_with_embedded_return(file_path):
    content = open_file(file_path)
    content = add_return_to_functions_with_callback_return(content)
    save_file(file_path, content)

def modify_model_functions(file_path):
    content = open_file(file_path)
    # Sequelize
    for seq in SEQUELIZEs:
        content = re.sub(seq[0], seq[1], content)
    # Globals
    for reg in GLOBALs:
        content = re.sub(reg[0], reg[1], content)
    for add_a_to in ADD_AWAIT_TO:
        content = re.sub(rf'\s\s{add_a_to}\.', rf' await {add_a_to}.', content)
    for add_r_to in ADD_AWAIT_TO:
        content = re.sub(rf'\s\s{add_r_to}\.', rf'  return {add_r_to}.', content)
    #

    content = re.sub(r'\ssequelize.query\.', r' await sequelize.query', content)
    content = re.sub(r'\s\srequest\(', r'  return request(', content)
    content = re.sub(r'\s\s await request\(', r'  return request(', content)
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(content)

def add_return_to_functions_with_callback_return(input_string):
    # Regex pattern to match functions with callback having a return statement
    pattern = re.compile(r'(\w+\.\w+\([\w\W]+?,\s*\([\w\W]+?\)\s*=>\s*\{[\w\W]+?return[\w\W]+?\}\s*\)\s*;)')
    # Function to add 'return' to the beginning of the matched text
    def replacer(match):
        return f'return {match.group(0)}'
    # Perform the replacement
    result = re.sub(pattern, replacer, input_string)
    return result


def revert_files_to_commit(file_paths, commit_hash):
    """
    Reverts a list of files in a Git repository to their state in a given commit.
    Parameters:
        - file_paths (list of str): List of file paths to revert.
        - commit_hash (str): The commit hash to revert the files to.
    """
    for file_path in file_paths:
        try:
            # Check if the file exists in the given commit
            subprocess.run(['git', 'cat-file', '-e', f'{commit_hash}:{file_path}'], check=True)

            # Checkout the file from the specified commit
            subprocess.run(['git', 'checkout', commit_hash, '--', file_path], check=True)
            print(f"Reverted {file_path} to commit {commit_hash}")
        except subprocess.CalledProcessError:
            print(f"Failed to revert {file_path} to commit {commit_hash}")

def test_regex(file):
    """
    Test the regex pattern against a list of examples.

    Parameters:
    - pattern (str): The regex pattern to test.
    - examples (list of str): The list of examples to test the pattern against.

    Returns:
    - matches (list of str): List of examples that match the pattern.
    """
    content = open_file(file)
    pattern = r',\n\s\s[a-zA-Z_]+\('
    # Custom replacement function
    def replacement_func(match):
        return ",\n  async" + match.group(0)[3:]
    # Replace all matches using the custom replacement function
    new_text = re.sub(pattern, replacement_func, content)
    save_file(file, new_text)
    return new_text


files = [
    "/Users/chazzromeo/OneCall/relayhealthcare-webapp-newest/model_functions/ride_details_functions.js",
]
file = "/Users/chazzromeo/OneCall/relayhealthcare-webapp-newest/model_functions/ride_details_functions.js"
# print(test_regex(file))
# run_globals(file)
run_sequelizer(file)
# modify_model_functions(file)
# add_return_to_response(file)

# for f in files:
#     modify_model_functions(f)

# commit_hash = "bd5b2cef1528f8b1b088f3bd666db45fd0aca5ab"
# revert_files_to_commit(files, commit_hash)
"""
Examples:

-> Callback functions (add return)
'recurrenceFn.getRecurrence({ id: data.recurrenceId, status: { [Sequelize.Op.notIn]: ['canceled'] } }, ['all'], async (err, recurrence) => {'
'commonRideHelper.generateRecurrenceRidesDates(recurrence, async (error, ridesObj) => {'
'OrgFnObj.getActiveOrgById(value, (org_data) => {'
'await ApptFnObj.getAppointmentAbstract({
              recurrence_id: data.recurrenceId,
              appointment_status: {[Sequelize.Op.notIn]: [statuses.APPOINTMENT_CANCELED.status]}
            }, ['id'], ['id', 'DESC'], undefined, async (flag, appointment) => {'


-> Normal functions (add await)
'providerUtil.getProvider(rideData);'


"""






