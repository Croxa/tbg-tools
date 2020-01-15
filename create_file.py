from helper_functions import *
from datetime import datetime
from time import sleep
import multiprocessing as mp


def write_binary(data, path, scaffolds, genes, scaffold_numbers, genes_numbers):
    """binary file:
    int i(how many scaffolds are there),
    i ints (how long are the strings of the scaffolds),
    characters for the scaffolds
    same thing for genes
    after that: format string: IIccccI?cccc
    --> scaffold number, position, base on ref, base in gene, position in triplet, amino acid, gene number,
        4ds, to A, to C, to G, to T"""

    # genes = {}
    # genes_list = []
    # scaffolds = {}
    # scaffolds_list = []
    # scaffolds_counter = 0
    # genes_counter = 0
    # for thread in data:
    #     for line in thread:
    #         line = line.strip()
    #         data_split = line.strip().split("\t")
    #         if data_split[0] not in scaffolds:
    #             scaffolds[data_split[0]] = scaffolds_counter
    #             scaffolds_counter += 1
    #             scaffolds_list.append(data_split[0])
    #         if data_split[6] not in genes:
    #             genes[data_split[6]] = genes_counter
    #             genes_counter += 1
    #             genes_list.append(data_split[6])
    fmt = format_string()
    with open(path, "wb") as f:
        f.write(struct.pack("I", len(genes)))
        f.write(struct.pack("I" * len(genes), *[len(genes_numbers[i]) for i in range(len(genes))]))
        for gene in range(len(genes)):
            f.write(struct.pack("c" * len(genes_numbers[gene]), *[bytes(i, "utf-8") for i in genes_numbers[gene]]))

        f.write(struct.pack("I", len(scaffolds)))
        f.write(struct.pack("I" * len(scaffolds), *[len(scaffold_numbers[i]) for i in range(len(scaffolds))]))
        for scaffold in range(len(scaffolds)):
            f.write(struct.pack("c" * len(scaffold_numbers[scaffold]), *[bytes(i, "utf-8") for i in scaffold_numbers[scaffold]]))
        for thread in data:

            for line in thread:
                data_split = line.strip().split("\t")
                for i in [5, 8, 9, 10, 11]:
                    if data_split[i] == "stop":
                        data_split[i] = "-"
                # data_split[0] = scaffolds[data_split[0]]
                data_split[0] = int(data_split[0])
                data_split[1] = int(data_split[1])
                # data_split[4] = int(data_split[4])
                #data_split[6] = genes[data_split[6]]
                data_split[6] = int(data_split[6])
                if data_split[7] == "True":
                    data_split[7] = True
                elif data_split[7] == "False":
                    data_split[7] = False
                single_char_list = []
                for i in data_split:
                    if type(i) == str:
                        a = [bytes(b, "utf-8") for b in i]
                        single_char_list.extend(a)

                    else:
                        single_char_list.append(i)

                try:
                    f.write(struct.pack(fmt, *single_char_list))
                except:
                    pass

    f.close()

def calculate_nucleotides(gene_sequences, aa_codes, gff_data, verbose, scaffolds, genes ):
    """nucleotide function for the multiprocessing"""
    outlist = []
    counter = 0
    printer = 0
    number_of_genes = len(gene_sequences.keys())
    for gene in gene_sequences.keys():
        if verbose:
            counter += 1.0
            if counter / number_of_genes >= printer:
                print(f"{round(printer * 100)}% done")
                printer += 0.05
        forward = gff_data[gene][1]
        for nucleotide in range(len(gene_sequences[gene])):
            scaff_id = scaffolds[gff_data[gene][2]]
            position = get_position_in_scaffold(gff_data[gene][0], nucleotide)

            triplett, position_in_triplett = get_current_triplett(gene_sequences[gene], nucleotide, forward)

            base = gene_sequences[gene][nucleotide].replace("U", "T")
            if forward:
                base_in_gene = base
            else:
                base_in_gene = str(get_other_strand(base)).replace("U", "T")

            amino_acid = get_code(triplett, aa_codes)
            if amino_acid is None:
                amino_acid = "+"
            gene_id = genes[gene]

            amino_acids = get_all_aa(triplett, position_in_triplett, aa_codes)

            four_ds = all([i == amino_acids[0] for i in amino_acids])
            A, C, G, T = amino_acids
            outlist.append("\t".join((str(i) for i in [scaff_id, position, base, base_in_gene,
                                                       position_in_triplett +1 , amino_acid, gene_id,
                                                       four_ds, A, C, G, T, "\n"])))


    return outlist



def create_the_file(gff_file, fasta_file, outfile_hr="default.tsv", outfile_bin="defailt.bin", verbose=False,
                    create_binary=False, write_tsv=True, aa_code="default", threads=1, protein=None):
    """Loading in all files and creating the tbg file and optionally a protein file and a human readable file"""
    time = datetime.now()
    #Load in all the files and data
    aa_codes = load_aa_codes(aa_code)
    try:
        gff_data = get_genes_and_cds(gff_file, verbose=verbose)
    except:
        raise Exception("Having trouble with loading in the data from the gff file.")
    try:
        fasta_data = load_fasta(fasta_file, seperator=" ", verbose=verbose)
    except:
        raise Exception("Having Trouble with loading in the data from the fasta file")
    gene_sequences = {}

    gene_to_number = {}
    number_to_gene = {}
    scaffold_to_number = {}
    number_to_scaffold = {}
    gene_counter = 0
    scaffold_counter = 0
    # get the sequence of every gene and filling dicts
    for gene in gff_data.keys():
        sequence = get_sequence_from_fasta(fasta_data[gff_data[gene][2]], gff_data[gene][0])
        gene_sequences[gene] = coding_strand_to_rna(sequence)
        if gene not in gene_to_number:
            gene_to_number[gene] = gene_counter
            number_to_gene[gene_counter] = gene
            gene_counter += 1
        if gff_data[gene][2] not in scaffold_to_number:
            scaffold_to_number[gff_data[gene][2]] = scaffold_counter
            number_to_scaffold[scaffold_counter] = gff_data[gene][2]
            scaffold_counter += 1

    write_gene = False

    # writing the protein file
    if protein is not None:
        if verbose:
            print("Starting to write protein_file")
        with open(protein, "w") as f:
            if write_gene:
                g = open("E_coli_genes.fa", "w")
            for gene in gene_sequences.keys():
                if gene == "maker-scaffold_186_motu5-augustus-gene-0.120-mRNA-1":
                    a = 1
                f.write(">" + gene + "\n")
                if write_gene:
                    g.write(">" + gene + "\n")
                if gff_data[gene][1]:

                    f.write(rna_to_protein(gene_sequences[gene], aa_codes) + "\n")
                    if write_gene:
                        g.write(gene_sequences[gene] + "\n")
                else:
                    f.write(rna_to_protein(get_other_strand(gene_sequences[gene]), aa_codes) + "\n")
                    if write_gene:
                        g.write(get_other_strand(gene_sequences[gene]) + "\n")

        f.close()
    #todo: intermediate files for pcs with low ram
    return
    # Distributing the genes on different dictionaries for the multiprocessing
    thread_gene_sequences_keys = [[]]
    for i in gene_sequences.keys():
        if len(thread_gene_sequences_keys[-1]) >= int(len(gene_sequences)/threads) + 1:
            thread_gene_sequences_keys.append([])
        thread_gene_sequences_keys[-1].append(i)

    thread_gene_sequences = []
    for i in range(len(thread_gene_sequences_keys)):
        thread_gene_sequences.append({})
        for j in thread_gene_sequences_keys[i]:
            thread_gene_sequences[i][j] = gene_sequences.pop(j)
    verboses = [False for i in range(threads)]
    verboses[0] = verbose

    #Calling the calculation for every nucleotide
    if verbose:
        print("Calculating the nucleotides (this may take a while)!")
    pool = mp.Pool(processes=len(thread_gene_sequences))
    results = [pool.apply_async(calculate_nucleotides, args=(thread_gene_sequences[x], aa_codes, gff_data, verboses[x],
                                                             scaffold_to_number, gene_to_number))
                                                            for x in range(len(thread_gene_sequences))]
    output = [p.get() for p in results]
    if verbose:
        print("100% done")

    #Output
    if create_binary:
        if verbose:
            print("Writing binary file")
        write_binary(output, outfile_bin, scaffold_to_number, gene_to_number, number_to_scaffold, number_to_gene)
    if write_tsv:
        if verbose:
            print("Writing human readable file")
        with open(outfile_hr, "w") as outf:
            for i in output:
                for j in i:
                    dummystring = j.split("\t")
                    dummystring[0] = number_to_scaffold[int(dummystring[0])]
                    dummystring[6] = number_to_gene[int(dummystring[6])]
                    outf.write("\t".join(dummystring))
        outf.close()
    #print((datetime.now()-time).total_seconds())





def write_human_readable(path_bin, path_hr=None):
    """loads in a tbg file and converts it to a human readable file"""
    if path_hr is None:
        path_hr = path_bin[:-3] + "tsv"
    with open(path_hr, "w") as outf:
        with open(path_bin, "rb") as f:
            genes = {}
            number_of_genes = struct.unpack("I", f.read(4))[0]
            genes_str_length = struct.unpack("I" * number_of_genes, f.read(4 * number_of_genes))
            for i in range(number_of_genes):
                gene_name = struct.unpack("c" * genes_str_length[i], f.read(genes_str_length[i]))
                gene_name = "".join([str(letter, "utf-8") for letter in gene_name])
                genes[i] = gene_name
            scaffolds = {}
            number_of_scaffolds = struct.unpack("I", f.read(4))[0]
            scaffolds_str_length = struct.unpack("I" * number_of_scaffolds, f.read(4 * number_of_scaffolds))
            for i in range(number_of_scaffolds):
                scaffold_name = struct.unpack("c" * scaffolds_str_length[i], f.read(scaffolds_str_length[i]))
                scaffold_name = "".join([str(letter, "utf-8") for letter in scaffold_name])
                scaffolds[i] = scaffold_name
            while True:
                scaffold_and_position = f.read(8)
                rest = f.read(byte_size_of_fmt(format_string()) - 8)
                if not scaffold_and_position or not rest:
                    # EOF
                    break
                scaffold_and_position = struct.unpack("II", scaffold_and_position)
                rest = [str(i) for i in  decode_line(rest, genes)]
                outf.write(scaffolds[scaffold_and_position[0]] + "\t" + str(scaffold_and_position[1]) + "\t" +
                               "\t".join(rest) + "\n")


if __name__ == "__main__":
    pass
